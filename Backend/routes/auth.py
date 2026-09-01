import uuid
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Form, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from Backend.database.mongodb import db

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Simple in-memory user store
USERS = {
    "vamsi": "vamsi_password",
    "geethanjali": "geethanjali_password"
}

# Fallback in-memory session store
ACTIVE_SESSIONS = {}

# MongoDB collections
sessions_collection = db["sessions"] if db is not None else None
users_collection = db["users"] if db is not None else None


def seed_default_users():
    """Ensure default users exist in MongoDB."""
    if users_collection is not None:
        try:
            for username, password in USERS.items():
                if not users_collection.find_one({"username": username}):
                    users_collection.insert_one({
                        "username": username,
                        "password": password,
                        "created_at": datetime.now(timezone.utc)
                    })
        except Exception:
            pass


try:
    seed_default_users()
except Exception:
    pass


def find_user(username: str) -> str | None:
    """Retrieve stored password for username from MongoDB or in-memory dict."""
    if users_collection is not None:
        try:
            user_doc = users_collection.find_one({"username": username})
            if user_doc:
                return user_doc.get("password")
        except Exception:
            pass
    return USERS.get(username)


def create_user(username: str, password: str) -> bool:
    """Save new user to MongoDB and in-memory dict."""
    USERS[username] = password
    if users_collection is not None:
        try:
            users_collection.update_one(
                {"username": username},
                {"$set": {
                    "username": username,
                    "password": password,
                    "created_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            return True
        except Exception:
            pass
    return True


def validate_username(username: str) -> tuple[bool, str]:
    """Validate username rules."""
    u = username.strip()
    if len(u) < 3 or len(u) > 30:
        return False, "Username must be between 3 and 30 characters."
    if not re.match(r"^[a-zA-Z0-9_.-]+$", u):
        return False, "Username can only contain letters, numbers, underscores, dashes, or dots."
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength (length, uppercase, lowercase, number, special character)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number (0-9)."
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*)."
    return True, ""


def get_session(token: str) -> str | None:
    if sessions_collection is not None:
        try:
            session = sessions_collection.find_one({"session_token": token})
            if session:
                return session["username"]
        except Exception:
            pass
    return ACTIVE_SESSIONS.get(token)


def set_session(token: str, username: str):
    if sessions_collection is not None:
        try:
            sessions_collection.insert_one({
                "session_token": token,
                "username": username,
                "created_at": datetime.now(timezone.utc)
            })
            return
        except Exception:
            pass
    ACTIVE_SESSIONS[token] = username


def delete_session(token: str):
    if sessions_collection is not None:
        try:
            sessions_collection.delete_one({"session_token": token})
            return
        except Exception:
            pass
    if token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]


def get_current_user_page(request: Request):
    token = request.cookies.get("session_token")
    username = get_session(token) if token else None
    if not username:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )
    return username


def get_current_user_api(request: Request):
    token = request.cookies.get("session_token")
    username = get_session(token) if token else None
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return username


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    token = request.cookies.get("session_token")
    username = get_session(token) if token else None
    if username:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"mode": "login"}
    )


@router.post("/login")
def login_post(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    u = username.strip()
    stored_password = find_user(u)
    if stored_password is not None and stored_password == password:
        token = str(uuid.uuid4())
        set_session(token, u)
        redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        redirect.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax"
        )
        return redirect

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "Invalid username or password",
            "mode": "login",
            "username": u
        }
    )


@router.get("/signup", response_class=HTMLResponse)
def signup_get(request: Request):
    token = request.cookies.get("session_token")
    username = get_session(token) if token else None
    if username:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"mode": "signup"}
    )


@router.post("/signup")
def signup_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(None)
):
    u = username.strip()

    # Validate username
    valid_u, u_err = validate_username(u)
    if not valid_u:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": u_err, "mode": "signup", "username": u}
        )

    # Check if username exists
    if find_user(u) is not None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": f"Username '{u}' is already registered. Please sign in.",
                "mode": "signup",
                "username": u
            }
        )

    # Check confirm password if supplied
    if confirm_password is not None and password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Passwords do not match.", "mode": "signup", "username": u}
        )

    # Validate password requirements (caps, numbers, special, len >= 8)
    valid_p, p_err = validate_password(password)
    if not valid_p:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": p_err, "mode": "signup", "username": u}
        )

    # Create the user
    create_user(u, password)

    # Automatically login new user
    token = str(uuid.uuid4())
    set_session(token, u)
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        samesite="lax"
    )
    return redirect


@router.get("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        delete_session(token)
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.delete_cookie(key="session_token")
    return redirect
