import uuid
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, Form, Response, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from Backend.database.mongodb import db
from Backend.services.session_service import (
    create_session,
    validate_session,
    destroy_session,
    purge_all_sessions,
    clean_expired_sessions
)
from Backend.services.oauth_service import (
    get_google_auth_url,
    get_github_auth_url,
    handle_google_callback,
    handle_github_callback,
    get_sandbox_user
)

logger = logging.getLogger(__name__)

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Default initial users
USERS = {
    "vamsi": "vamsi_password",
    "geethanjali": "geethanjali_password"
}

# MongoDB user collection reference
def get_users_collection():
    if db is not None:
        try:
            return db["users"]
        except Exception:
            pass
    return None


def seed_default_users():
    """Ensure default users exist in MongoDB."""
    col = get_users_collection()
    if col is not None:
        try:
            for username, password in USERS.items():
                if not col.find_one({"username": username}):
                    col.insert_one({
                        "username": username,
                        "password": password,
                        "auth_type": "local",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    })
        except Exception as e:
            logger.warning(f"Error seeding default users: {e}")


try:
    seed_default_users()
except Exception:
    pass


def find_user(username: str) -> Optional[dict]:
    """Retrieve user dictionary from MongoDB or in-memory fallback."""
    col = get_users_collection()
    if col is not None:
        try:
            doc = col.find_one({"username": username})
            if doc:
                return doc
        except Exception:
            pass

    if username in USERS:
        return {"username": username, "password": USERS[username], "auth_type": "local"}
    return None


def create_user(username: str, password: Optional[str] = None, auth_type: str = "local", email: Optional[str] = None) -> bool:
    """Save new user to MongoDB and fallback memory."""
    if password:
        USERS[username] = password

    col = get_users_collection()
    if col is not None:
        try:
            user_doc = {
                "username": username,
                "auth_type": auth_type,
                "email": email or f"{username}@predictops.local",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            if password:
                user_doc["password"] = password

            col.update_one(
                {"username": username},
                {"$set": user_doc},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Error creating user in MongoDB: {e}")
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


def get_session(token: str) -> Optional[str]:
    """Retrieves validated username from session service."""
    return validate_session(token)


def set_session(token: str, username: str, remember_me: bool = False, provider: str = "local"):
    """Legacy helper that creates a session with custom duration."""
    return create_session(username, remember_me=remember_me, provider=provider)


def delete_session(token: str):
    """Destroys an active session."""
    destroy_session(token)


def clear_all_sessions():
    """Purges all sessions on server startup."""
    purge_all_sessions()


def get_current_user_page(request: Request) -> str:
    """Dependency for protected HTML routes."""
    token = request.cookies.get("session_token")
    username = validate_session(token) if token else None
    if not username:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )
    return username


def get_current_user_api(request: Request) -> str:
    """Dependency for protected JSON API routes."""
    token = request.cookies.get("session_token")
    username = validate_session(token) if token else None
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return username


# =========================================================================
# Standard Authentication Routes
# =========================================================================

@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    token = request.cookies.get("session_token")
    username = validate_session(token) if token else None
    if username:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"mode": "login"}
    )


@router.post("/login")
def login_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: Optional[str] = Form(None)
):
    u = username.strip()
    user_doc = find_user(u)

    if user_doc and user_doc.get("password") == password:
        is_remember = remember_me in ["on", "true", "1", "yes"]
        token, max_age = create_session(u, remember_me=is_remember, provider="local")

        redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        redirect.set_cookie(
            key="session_token",
            value=token,
            max_age=max_age,
            httponly=True,
            samesite="lax",
            path="/"
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
    username = validate_session(token) if token else None
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
    confirm_password: Optional[str] = Form(None)
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

    # Validate password requirements
    valid_p, p_err = validate_password(password)
    if not valid_p:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": p_err, "mode": "signup", "username": u}
        )

    # Create the user
    create_user(u, password=password, auth_type="local")

    # Automatically create session for new user
    token, max_age = create_session(u, remember_me=False, provider="local")
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="session_token",
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/"
    )
    return redirect


@router.get("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        destroy_session(token)
    redirect = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    redirect.delete_cookie(key="session_token", path="/")
    redirect.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    redirect.headers["Pragma"] = "no-cache"
    redirect.headers["Expires"] = "0"
    return redirect


# =========================================================================
# OAuth 2.0 Authentication Routes
# =========================================================================

@router.get("/auth/oauth/sandbox")
def oauth_sandbox(provider: str = "demo"):
    """
    Developer Sandbox OAuth 2.0 Flow:
    Provides an immediate 1-click verified login for testing and evaluation.
    """
    profile = get_sandbox_user(provider)
    username = profile["username"]

    # Provision user
    create_user(username, auth_type=profile["provider"], email=profile["email"])

    # Establish session
    token, max_age = create_session(username, remember_me=True, provider=profile["provider"])
    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="session_token",
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/"
    )
    logger.info(f"OAuth 2.0 Sandbox login successful for {username} ({profile['provider']})")
    return redirect


@router.get("/auth/oauth/demo")
def oauth_demo():
    """Direct alias for 1-click sandbox demo."""
    return oauth_sandbox(provider="demo")


@router.get("/auth/oauth/google/callback")
async def oauth_google_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Handles Google OAuth 2.0 callback redirect."""
    if error or not code:
        logger.warning(f"Google OAuth denied or cancelled: {error}")
        return RedirectResponse(url="/login?error=google_auth_failed", status_code=status.HTTP_302_FOUND)

    profile = await handle_google_callback(code)
    if not profile:
        return RedirectResponse(url="/login?error=google_profile_fetch_failed", status_code=status.HTTP_302_FOUND)

    username = profile["username"]
    create_user(username, auth_type="google", email=profile.get("email"))

    token, max_age = create_session(username, remember_me=True, provider="google")
    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="session_token",
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/"
    )
    return redirect


@router.get("/auth/oauth/github/callback")
async def oauth_github_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    """Handles GitHub OAuth 2.0 callback redirect."""
    if error or not code:
        logger.warning(f"GitHub OAuth denied or cancelled: {error}")
        return RedirectResponse(url="/login?error=github_auth_failed", status_code=status.HTTP_302_FOUND)

    profile = await handle_github_callback(code)
    if not profile:
        return RedirectResponse(url="/login?error=github_profile_fetch_failed", status_code=status.HTTP_302_FOUND)

    username = profile["username"]
    create_user(username, auth_type="github", email=profile.get("email"))

    token, max_age = create_session(username, remember_me=True, provider="github")
    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="session_token",
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/"
    )
    return redirect


@router.get("/auth/oauth/{provider}")
def oauth_authorize(provider: str):
    """Initiates OAuth 2.0 authorization code flow for requested provider."""
    provider_clean = provider.lower().strip()
    if provider_clean == "google":
        url = get_google_auth_url()
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    elif provider_clean == "github":
        url = get_github_auth_url()
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    elif provider_clean in ["demo", "sandbox"]:
        return RedirectResponse(url="/auth/oauth/sandbox?provider=demo", status_code=status.HTTP_302_FOUND)
    else:
        return RedirectResponse(url="/login?error=unsupported_provider", status_code=status.HTTP_302_FOUND)
