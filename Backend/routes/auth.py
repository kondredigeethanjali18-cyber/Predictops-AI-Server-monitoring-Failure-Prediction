import uuid
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

# MongoDB sessions collection
sessions_collection = db["sessions"] if db is not None else None

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
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )

@router.post("/login")
def login_post(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
    if username in USERS and USERS[username] == password:
        token = str(uuid.uuid4())
        set_session(token, username)
        redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
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
        context={"error": "Invalid username or password"}
    )

@router.get("/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        delete_session(token)
    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.delete_cookie(key="session_token")
    return redirect
