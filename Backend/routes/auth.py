import uuid
import re
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, Form, Response, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
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
    get_sandbox_user,
    GOOGLE_CLIENT_ID,
    GITHUB_CLIENT_ID
)
from Backend.services.email_verification_service import (
    verify_email_exists,
    create_verification_record,
    send_verification_email,
    verify_email_code
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


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email address format, structure, and domain existence."""
    e = email.strip()
    if not e:
        return False, "Email address is required."
    return verify_email_exists(e)



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
    """Creates a session with custom duration."""
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
def login_get(request: Request, success: Optional[str] = None, error: Optional[str] = None):
    token = request.cookies.get("session_token")
    username = validate_session(token) if token else None
    if username:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "mode": "login",
            "success": success,
            "error": error
        }
    )


@router.post("/login")
def login_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    u = username.strip()
    user_doc = find_user(u)

    if user_doc and user_doc.get("password") == password:
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
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: Optional[str] = Form(None)
):
    u = username.strip()
    e = email.strip()

    # Validate username
    valid_u, u_err = validate_username(u)
    if not valid_u:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": u_err, "mode": "signup", "username": u, "email": e}
        )

    # Validate email
    valid_e, e_err = validate_email(e)
    if not valid_e:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": e_err, "mode": "signup", "username": u, "email": e}
        )

    # Check if username exists
    if find_user(u) is not None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": f"Username '{u}' is already registered. Please sign in.",
                "mode": "signup",
                "username": u,
                "email": e
            }
        )

    # Check confirm password if supplied
    if confirm_password is not None and password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Passwords do not match.", "mode": "signup", "username": u, "email": e}
        )

    # Validate password requirements
    valid_p, p_err = validate_password(password)
    if not valid_p:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": p_err, "mode": "signup", "username": u, "email": e}
        )

    # Create the user in database with email
    create_user(u, password=password, auth_type="local", email=e)

    # Redirect to Login Page with Success message as requested
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "success": f"Account created successfully for '{u}'! Please sign in with your credentials.",
            "mode": "login",
            "username": u
        }
    )


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
# OAuth 2.0 & Google 2-Step Verification Routes
# =========================================================================

@router.post("/auth/oauth/google/send-code")
async def google_send_verification_code(request: Request):
    """
    Verifies that the Google email exists and has active MX mail records,
    then generates and dispatches a 6-digit OTP verification code directly to the inbox.
    """
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            email = data.get("email", "").strip()
        else:
            form = await request.form()
            email = form.get("email", "").strip()
    except Exception:
        email = ""

    if not email:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Please enter your Google email address."}
        )

    # 1. Verify that email format & domain exist with active MX mail servers
    is_valid, err_msg = verify_email_exists(email)
    if not is_valid:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": err_msg}
        )

    clean_email = email.lower().strip()

    # 2. Generate secure OTP and store record (10-min validity)
    code, expires_at = create_verification_record(clean_email)

    # 3. Dispatch verification email via SMTP directly to the inbox
    res_tuple = send_verification_email(clean_email, code)
    if len(res_tuple) == 3:
        sent, delivery_msg, delivered_via_smtp = res_tuple
    else:
        sent, delivery_msg = res_tuple
        delivered_via_smtp = False

    if not sent:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": delivery_msg}
        )

    # Mask email for privacy (e.g., va***ops@gmail.com)
    parts = clean_email.split("@")
    local_part = parts[0]
    domain_part = parts[1]
    if len(local_part) <= 3:
        masked = f"{local_part[0]}***@{domain_part}"
    else:
        masked = f"{local_part[:2]}***{local_part[-2:]}@{domain_part}"

    response_payload = {
        "success": True,
        "message": f"A 6-digit confirmation code has been sent to {clean_email}." if delivered_via_smtp else f"Verification code generated for {clean_email}.",
        "email": clean_email,
        "masked_email": masked,
        "delivered_via_smtp": delivered_via_smtp,
        "expires_in_seconds": 600
    }

    return JSONResponse(content=response_payload)



@router.post("/auth/oauth/google/verify-code")
async def google_verify_code(request: Request, response: Response):
    """
    Validates the 6-digit verification code, provisions user in MongoDB,
    establishes an authenticated session, and returns login redirection.
    """
    try:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            email = data.get("email", "").strip()
            code = data.get("code", "").strip()
        else:
            form = await request.form()
            email = form.get("email", "").strip()
            code = form.get("code", "").strip()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Invalid request payload."}
        )

    if not email or not code:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Email address and 6-digit code are required."}
        )

    is_valid, err_msg = verify_email_code(email, code)
    if not is_valid:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": err_msg}
        )

    # Email verified! Provision or update user
    username = email.split("@")[0].replace(".", "_").lower()
    create_user(username, auth_type="google", email=email)

    # Create active session
    token, max_age = create_session(username, remember_me=True, provider="google")

    res = JSONResponse(content={
        "success": True,
        "message": "Account verified successfully! Logging you in...",
        "redirect_url": "/dashboard",
        "username": username,
        "email": email
    })
    res.set_cookie(
        key="session_token",
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/"
    )
    logger.info(f"Google 2-Step OTP login successful for {username} ({email})")
    return res


@router.post("/auth/oauth/prompt-submit")
def oauth_prompt_submit(
    request: Request,
    provider: str = Form(...),
    account_input: str = Form(...)
):
    """
    Handles user's submitted Google or GitHub account identity when clicking OAuth buttons.
    """
    p = provider.lower().strip()
    raw_acc = account_input.strip()

    if not raw_acc:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": f"Please enter your {p.capitalize()} account.", "mode": "login"}
        )

    # Extract clean username from email or handle
    if p == "google":
        email = raw_acc if "@" in raw_acc else f"{raw_acc}@gmail.com"
        username = email.split("@")[0].replace(".", "_").lower()
        auth_type = "google"
        display_name = f"Google User ({email})"
    elif p == "github":
        username = raw_acc.split("@")[0].replace(" ", "_").lower()
        email = raw_acc if "@" in raw_acc else f"{username}@github.local"
        auth_type = "github"
        display_name = f"GitHub User (@{username})"
    else:
        username = raw_acc.replace(" ", "_").lower()
        email = f"{username}@predictops.local"
        auth_type = "oauth_demo"
        display_name = username

    # Provision user in database
    create_user(username, auth_type=auth_type, email=email)

    # Establish active session (7-day remember-me)
    token, max_age = create_session(username, remember_me=True, provider=auth_type)
    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="session_token",
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/"
    )
    logger.info(f"OAuth Account login successful for {username} via {auth_type} ({email})")
    return redirect


@router.get("/auth/oauth/sandbox")
@router.get("/auth/oauth/demo")
def oauth_instant_disabled():
    """Instant login is permanently disabled. Redirects to standard login."""
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


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


@router.get("/auth/oauth/google", response_class=HTMLResponse)
@router.get("/auth/google-login", response_class=HTMLResponse)
def google_login_page(request: Request):
    """
    Dedicated Google Sign-in and 2-Step OTP Verification Page.
    """
    token = request.cookies.get("session_token")
    username = validate_session(token) if token else None
    if username:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request=request,
        name="google_login.html",
        context={}
    )


@router.get("/auth/oauth/{provider}")
def oauth_authorize(provider: str):
    """Initiates OAuth 2.0 authorization code flow or account prompt for requested provider."""
    provider_clean = provider.lower().strip()
    if provider_clean == "google":
        return RedirectResponse(url="/auth/oauth/google", status_code=status.HTTP_302_FOUND)
    elif provider_clean == "github":
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    elif provider_clean in ["demo", "sandbox"]:
        return RedirectResponse(url="/auth/oauth/sandbox?provider=demo", status_code=status.HTTP_302_FOUND)
    else:
        return RedirectResponse(url="/login?error=unsupported_provider", status_code=status.HTTP_302_FOUND)

