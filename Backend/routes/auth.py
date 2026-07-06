import uuid
import re
import hashlib
import secrets
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Form, Response, HTTPException, status, Query, Depends, Path as FPath
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from Backend.database.mongodb import db
from Backend.services.rbac_service import (
    ROLES,
    VALID_ROLES,
    VIEWER_PERMISSIONS,
    DEVOPS_PERMISSIONS,
    ADMIN_PERMISSIONS,
    normalize_role,
    get_role_permissions,
    has_permission,
    get_role_badge_label,
    get_role_display_name
)
from Backend.services.session_service import (
    create_session,
    validate_session,
    validate_session_data,
    destroy_session,
    purge_all_sessions,
    purge_user_sessions,
    clean_expired_sessions,
    ACTIVE_SESSIONS
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
from Backend.services.audit_service import (
    record_audit_log,
    get_recent_audit_logs,
    record_incident_action,
    get_all_incident_actions
)
from Backend.services.cache_service import CacheService
from Backend.services.chaos_service import inject_chaos_telemetry_spike
from Backend.services.prediction_service import (
    run_ml_diagnostics,
    trigger_ml_retrain,
    hot_reload_model
)

logger = logging.getLogger(__name__)

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# =========================================================================
# Password Hashing & Verification Utilities
# =========================================================================

def hash_password(password: str) -> str:
    """Generates salted SHA-256 hash for secure password storage."""
    salt = secrets.token_hex(8)
    pwd_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}:{pwd_hash}"


def verify_password(plain_password: str, stored_val: str) -> bool:
    """Verifies a plaintext password against salted hash or fallback plain string."""
    if not stored_val or not plain_password:
        return False
    if ":" in stored_val:
        try:
            salt, expected_hash = stored_val.split(":", 1)
            actual_hash = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
            return secrets.compare_digest(actual_hash, expected_hash)
        except Exception:
            return False
    # Backward compatibility with un-hashed test passwords
    return secrets.compare_digest(plain_password, stored_val)


# =========================================================================
# Default Seeded Users & MongoDB Data Helpers
# =========================================================================

USERS = {
    "vamsi": "vamsi_password",
    "geethanjali": "geethanjali_password"
}

USER_ROLES = {
    "vamsi": "admin",
    "geethanjali": "devops"
}

USER_STATUS = {
    "vamsi": True,
    "geethanjali": True
}


def get_users_collection():
    if db is not None:
        try:
            return db["users"]
        except Exception:
            pass
    return None


def seed_default_users():
    """Ensure default users exist in MongoDB with roles and active status."""
    col = get_users_collection()
    if col is not None:
        try:
            for username, password in USERS.items():
                assigned_role = USER_ROLES.get(username, "viewer")
                existing = col.find_one({"username": username})
                now_str = datetime.now(timezone.utc).isoformat()
                if not existing:
                    col.insert_one({
                        "username": username,
                        "password_hash": hash_password(password),
                        "password": password,
                        "role": assigned_role,
                        "email": f"{username}@predictops.local",
                        "is_active": True,
                        "auth_type": "local",
                        "created_at": now_str,
                        "updated_at": now_str
                    })
                else:
                    updates = {}
                    if "role" not in existing or existing["role"] != assigned_role:
                        updates["role"] = assigned_role
                    if "is_active" not in existing:
                        updates["is_active"] = True
                    if "password_hash" not in existing:
                        updates["password_hash"] = hash_password(password)
                    if updates:
                        updates["updated_at"] = now_str
                        col.update_one({"username": username}, {"$set": updates})
        except Exception as e:
            logger.warning(f"Error seeding default users: {e}")


try:
    seed_default_users()
except Exception:
    pass


def find_user(username_or_id: str) -> Optional[dict]:
    """Retrieve user dictionary from MongoDB or in-memory fallback."""
    if not username_or_id:
        return None
    col = get_users_collection()
    if col is not None:
        try:
            doc = col.find_one({"username": username_or_id})
            if not doc:
                try:
                    from bson import ObjectId
                    doc = col.find_one({"_id": ObjectId(username_or_id)})
                except Exception:
                    pass
            if doc:
                doc["role"] = normalize_role(doc.get("role", "viewer"))
                doc["is_active"] = doc.get("is_active", True)
                return doc
        except Exception:
            pass

    if username_or_id in USERS:
        return {
            "username": username_or_id,
            "password": USERS[username_or_id],
            "password_hash": hash_password(USERS[username_or_id]),
            "role": USER_ROLES.get(username_or_id, "viewer"),
            "email": f"{username_or_id}@predictops.local",
            "is_active": USER_STATUS.get(username_or_id, True),
            "auth_type": "local"
        }
    return None


def create_user(
    username: str,
    password: Optional[str] = None,
    auth_type: str = "local",
    email: Optional[str] = None,
    role: str = "viewer",
    is_active: bool = True
) -> bool:
    """Save or update user in MongoDB and fallback memory with role and active status."""
    clean_role = normalize_role(role)
    if password:
        USERS[username] = password
    USER_ROLES[username] = clean_role
    USER_STATUS[username] = is_active

    col = get_users_collection()
    if col is not None:
        try:
            now_str = datetime.now(timezone.utc).isoformat()
            user_doc = {
                "username": username,
                "role": clean_role,
                "is_active": is_active,
                "auth_type": auth_type,
                "email": email or f"{username}@predictops.local",
                "created_at": now_str,
                "updated_at": now_str
            }
            if password:
                user_doc["password_hash"] = hash_password(password)
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


RESERVED_USERNAMES = {
    "admin", "administrator", "root", "system", "superuser",
    "null", "undefined", "anonymous", "guest", "api", "bot",
    "support", "help", "security", "predictops"
}


def validate_username(username: str) -> tuple[bool, str]:
    """Validate username rules: characters or mixed, numbers-only invalid, special char bounds."""
    u = username.strip()
    if len(u) < 3:
        return False, "Username must be at least 3 characters long."
    if len(u) > 30:
        return False, "Username cannot exceed 30 characters."
    if not re.match(r"^[a-zA-Z0-9_.-]+$", u):
        return False, "Username can only contain letters, numbers, underscores, dashes, or dots."
    if not any(c.isalpha() for c in u):
        return False, "Username cannot be numbers only. It must contain letters or mixed characters (e.g. user123)."
    if u[0] in "_.-" or u[-1] in "_.-":
        return False, "Username must start and end with a letter or number."
    if re.search(r"[_.-]{2,}", u):
        return False, "Username cannot contain consecutive special characters (such as '..' or '__')."
    if u.lower() in RESERVED_USERNAMES and find_user(u) is None:
        return False, f"Username '{u}' is reserved for system use. Please choose a different username."
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    """Validate email address format, structure, and domain existence."""
    e = email.strip().lower()
    if not e:
        return False, "Email address is required."
    if len(e) > 100:
        return False, "Email address cannot exceed 100 characters."
    if " " in e:
        return False, "Email address cannot contain spaces."

    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, e):
        return False, "Invalid email address format (e.g. user@domain.com)."

    parts = e.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False, "Invalid email address format."

    local_part, domain = parts[0], parts[1]
    if local_part.startswith(".") or local_part.endswith(".") or ".." in local_part:
        return False, "Email username cannot start, end, or contain consecutive dots."

    domain_parts = domain.split(".")
    if len(domain_parts) < 2 or len(domain_parts[-1]) < 2 or not domain_parts[-1].isalpha():
        return False, "Email must have a valid top-level domain (e.g., .com, .org, .net, .in)."

    return verify_email_exists(e)


def validate_password(password: str, username: Optional[str] = None) -> tuple[bool, str]:
    """Validate password strength (length, uppercase, lowercase, number, special character, divergence)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number (0-9)."
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*)."
    if username and len(username) >= 3 and username.lower() in password.lower():
        return False, "Password cannot contain your username."
    return True, ""


# =========================================================================
# UserSession Helper & RBAC Dependencies
# =========================================================================

class UserSession(dict):
    """
    Authenticated User Session object with direct property access, dictionary compatibility,
    and automatic permission mapping.
    """
    def __init__(
        self,
        username: str,
        role: str = "viewer",
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        is_active: bool = True,
        provider: str = "local",
        **kwargs
    ):
        clean_role = normalize_role(role)
        perms = get_role_permissions(clean_role)
        badge = get_role_badge_label(clean_role)
        display_name = get_role_display_name(clean_role)

        super().__init__(
            id=user_id or username,
            username=username,
            email=email or f"{username}@predictops.local",
            role=clean_role,
            role_badge=badge,
            role_display=display_name,
            is_active=is_active,
            provider=provider,
            permissions=perms,
            **kwargs
        )
        self.id = user_id or username
        self.username = username
        self.email = email or f"{username}@predictops.local"
        self.role = clean_role
        self.role_badge = badge
        self.role_display = display_name
        self.is_active = is_active
        self.provider = provider
        self.permissions = perms

    def has_permission(self, permission: str) -> bool:
        return has_permission(self.role, permission)

    def __str__(self) -> str:
        return self.username

    def __repr__(self) -> str:
        return f"UserSession(username='{self.username}', role='{self.role}', active={self.is_active})"


def get_session(token: str) -> Optional[str]:
    """Retrieves validated username from session service."""
    return validate_session(token)


def set_session(token: str, username: str, remember_me: bool = False, provider: str = "local", role: str = "viewer"):
    """Creates a session with custom duration and role."""
    return create_session(username, role=normalize_role(role), remember_me=remember_me, provider=provider)


def delete_session(token: str):
    """Destroys an active session."""
    destroy_session(token)


def clear_all_sessions():
    """Purges all sessions on server startup."""
    purge_all_sessions()


def get_current_user_session(request: Request) -> Optional[UserSession]:
    """
    Extracts, validates, and resolves the current authenticated user session.
    Enforces active user account check: deactivated accounts are immediately rejected.
    """
    auth_hdr = request.headers.get("Authorization", "")
    token = None
    if auth_hdr.startswith("Bearer "):
        token = auth_hdr[7:].strip()
    if not token:
        token = request.cookies.get("session_token")

    if not token:
        return None

    session_data = validate_session_data(token)
    if not session_data:
        return None

    username = session_data.get("username")
    if not username:
        return None

    # Verify user record in database
    user_doc = find_user(username)
    if not user_doc:
        destroy_session(token)
        return None

    # Security check: Deactivated users cannot authenticate or maintain sessions
    if not user_doc.get("is_active", True):
        destroy_session(token)
        logger.warning(f"Deactivated user '{username}' attempted access with valid token. Session terminated.")
        return None

    role = normalize_role(user_doc.get("role", session_data.get("role", "viewer")))
    email = user_doc.get("email", f"{username}@predictops.local")
    user_id = str(user_doc.get("_id", username))

    return UserSession(
        username=username,
        role=role,
        user_id=user_id,
        email=email,
        is_active=True,
        provider=session_data.get("provider", "local")
    )


def get_current_user_page(request: Request) -> UserSession:
    """Dependency for protected HTML routes. Redirects to /login if unauthenticated."""
    user_session = get_current_user_session(request)
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": "/login"}
        )
    return user_session


def get_current_user_api(request: Request) -> UserSession:
    """Dependency for protected JSON API routes. Returns 401 if unauthenticated."""
    user_session = get_current_user_session(request)
    if not user_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return user_session


def require_permission(permission: str):
    """
    Central RBAC Permission Enforcer.
    Validates that the authenticated user possesses the specific permission identifier.
    Returns 401 if unauthenticated, 403 if permission is missing.
    """
    def permission_checker(request: Request) -> UserSession:
        user_session = get_current_user_session(request)
        if not user_session:
            accept_hdr = request.headers.get("accept", "")
            if "text/html" in accept_hdr and "application/json" not in accept_hdr:
                raise HTTPException(
                    status_code=status.HTTP_302_FOUND,
                    headers={"Location": "/login"}
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        if not user_session.has_permission(permission):
            logger.warning(
                f"RBAC DENIED: User '{user_session.username}' (role: '{user_session.role}') "
                f"attempted to access {request.url.path} requiring permission '{permission}'"
            )
            accept_hdr = request.headers.get("accept", "")
            if "text/html" in accept_hdr and "application/json" not in accept_hdr:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: Your role ({user_session.role_badge}) is not authorized to access this resource."
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Missing required permission: '{permission}'"
            )
        return user_session
    return permission_checker


def require_role(allowed_roles: List[str]):
    """
    Role-Based Access Control Dependency Factory checking membership in allowed roles.
    """
    normalized_allowed = [normalize_role(r) for r in allowed_roles]

    def role_checker(request: Request) -> UserSession:
        user_session = get_current_user_session(request)
        if not user_session:
            accept_hdr = request.headers.get("accept", "")
            if "text/html" in accept_hdr and "application/json" not in accept_hdr:
                raise HTTPException(
                    status_code=status.HTTP_302_FOUND,
                    headers={"Location": "/login"}
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        if user_session.role not in normalized_allowed:
            logger.warning(
                f"RBAC DENIED: User '{user_session.username}' (role: '{user_session.role}') "
                f"attempted to access {request.url.path} requiring roles {allowed_roles}"
            )
            accept_hdr = request.headers.get("accept", "")
            if "text/html" in accept_hdr and "application/json" not in accept_hdr:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access Denied: Your role ({user_session.role_badge}) is not authorized to access this resource."
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return user_session
    return role_checker


# =========================================================================
# Identity & Authentication Routes
# =========================================================================

@router.get("/auth/me")
@router.get("/api/auth/me")
def get_auth_me(current_user: UserSession = Depends(get_current_user_api)):
    """
    Returns full identity, role, and permission matrix for the authenticated user.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "role_badge": current_user.role_badge,
        "role_display": current_user.role_display,
        "is_active": current_user.is_active,
        "permissions": current_user.permissions
    }


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request, success: Optional[str] = None, error: Optional[str] = None):
    user_session = get_current_user_session(request)
    if user_session:
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
async def login_post(
    request: Request,
    response: Response,
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    login_portal: Optional[str] = Form("viewer")
):
    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept", "")
    is_json = "application/json" in content_type or "application/json" in accept_header

    u = (username or "").strip()
    p = password or ""
    portal = (login_portal or "viewer").strip().lower()

    if not u or not p:
        try:
            if "application/json" in content_type:
                body_json = await request.json()
                if isinstance(body_json, dict):
                    if not u:
                        u = (body_json.get("username") or "").strip()
                    if not p:
                        p = body_json.get("password") or ""
                    if not login_portal or login_portal == "viewer":
                        portal = (body_json.get("login_portal") or body_json.get("portal") or body_json.get("role") or "viewer").strip().lower()
        except Exception:
            pass

    normalized_portal = normalize_role(portal)

    if not u or not p:
        if is_json:
            return JSONResponse(
                status_code=400,
                content={"detail": "Username and password are required.", "success": False}
            )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Please enter both username and password.",
                "mode": "login",
                "username": u,
                "login_portal": normalized_portal
            }
        )

    user_doc = find_user(u)

    if user_doc:
        # Check if user is deactivated
        if not user_doc.get("is_active", True):
            if is_json:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Account is deactivated. Contact an administrator.", "success": False}
                )
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={
                    "error": "Account is deactivated. Contact an administrator.",
                    "mode": "login",
                    "username": u,
                    "login_portal": normalized_portal
                }
            )

        stored_hash = user_doc.get("password_hash") or user_doc.get("password", "")
        if verify_password(p, stored_hash):
            user_role = normalize_role(user_doc.get("role", USER_ROLES.get(u, "viewer")))

            # Enforce Portal-Specific Role Authorization
            if normalized_portal == "admin" and user_role != "admin":
                err_msg = f"Access Denied: Account '{u}' has '{get_role_badge_label(user_role)}' role and is not authorized for the Administrator Portal. Please use the {get_role_display_name(user_role)} portal."
                if is_json:
                    return JSONResponse(status_code=403, content={"detail": err_msg, "success": False, "role": user_role})
                return templates.TemplateResponse(
                    request=request,
                    name="login.html",
                    context={
                        "error": err_msg,
                        "mode": "login",
                        "username": u,
                        "login_portal": normalized_portal
                    }
                )

            if normalized_portal == "devops" and user_role not in ("devops", "admin"):
                err_msg = f"Access Denied: Account '{u}' has '{get_role_badge_label(user_role)}' role and is not authorized for the DevOps Engineer Portal. Please use the Viewer / Analyst portal."
                if is_json:
                    return JSONResponse(status_code=403, content={"detail": err_msg, "success": False, "role": user_role})
                return templates.TemplateResponse(
                    request=request,
                    name="login.html",
                    context={
                        "error": err_msg,
                        "mode": "login",
                        "username": u,
                        "login_portal": normalized_portal
                    }
                )

            token, max_age = create_session(u, role=user_role, remember_me=False, provider="local")

            record_audit_log(
                operator=u,
                role=user_role,
                action="PORTAL_LOGIN",
                details=f"User signed into {normalized_portal.upper()} portal (Account Role: {user_role.upper()})",
                target="auth"
            )

            redirect_target = "/admin" if (user_role == "admin" and normalized_portal == "admin") else "/dashboard"

            if is_json:
                json_resp = JSONResponse(
                    content={
                        "success": True,
                        "message": f"Login successful as {get_role_display_name(user_role)}",
                        "username": u,
                        "role": user_role,
                        "role_badge": get_role_badge_label(user_role),
                        "role_display": get_role_display_name(user_role),
                        "portal": normalized_portal,
                        "permissions": get_role_permissions(user_role),
                        "token": token,
                        "redirect_url": redirect_target
                    }
                )
                json_resp.set_cookie(
                    key="session_token",
                    value=token,
                    max_age=max_age,
                    httponly=True,
                    samesite="lax",
                    path="/"
                )
                return json_resp

            redirect = RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)
            redirect.set_cookie(
                key="session_token",
                value=token,
                max_age=max_age,
                httponly=True,
                samesite="lax",
                path="/"
            )
            return redirect

    if is_json:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid username or password.", "success": False}
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": "Invalid username or password",
            "mode": "login",
            "username": u,
            "login_portal": normalized_portal
        }
    )


@router.get("/signup", response_class=HTMLResponse)
def signup_get(request: Request):
    user_session = get_current_user_session(request)
    if user_session:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"mode": "signup"}
    )


@router.post("/signup")
async def signup_post(
    request: Request,
    response: Response,
    username: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    confirm_password: Optional[str] = Form(None),
    role: Optional[str] = Form("viewer")
):
    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept", "")
    is_json = "application/json" in content_type or "application/json" in accept_header

    u = (username or "").strip()
    e = (email or "").strip()
    p = password or ""
    cp = confirm_password or ""
    r = (role or "viewer").strip().lower()

    if not u or not e or not p:
        try:
            if "application/json" in content_type:
                body_json = await request.json()
                if isinstance(body_json, dict):
                    if not u:
                        u = (body_json.get("username") or "").strip()
                    if not e:
                        e = (body_json.get("email") or "").strip()
                    if not p:
                        p = body_json.get("password") or ""
                    if not cp:
                        cp = body_json.get("confirm_password") or ""
                    if not role or role == "viewer":
                        r = (body_json.get("role") or "viewer").strip().lower()
        except Exception:
            pass

    if not u or not e or not p:
        if is_json:
            return JSONResponse(
                status_code=400,
                content={"detail": "Username, email, and password are required.", "success": False}
            )
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "All fields (username, email, password) are required.",
                "mode": "signup",
                "username": u,
                "email": e
            }
        )

    # Validate username
    valid_u, u_err = validate_username(u)
    if not valid_u:
        if is_json:
            return JSONResponse(status_code=400, content={"detail": u_err, "success": False})
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": u_err, "mode": "signup", "username": u, "email": e}
        )

    # Validate email
    valid_e, e_err = validate_email(e)
    if not valid_e:
        if is_json:
            return JSONResponse(status_code=400, content={"detail": e_err, "success": False})
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": e_err, "mode": "signup", "username": u, "email": e}
        )

    # Check if username exists
    if find_user(u) is not None:
        if is_json:
            return JSONResponse(status_code=400, content={"detail": f"Username '{u}' is already registered.", "success": False})
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
    if cp and p != cp:
        if is_json:
            return JSONResponse(status_code=400, content={"detail": "Passwords do not match.", "success": False})
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Passwords do not match.", "mode": "signup", "username": u, "email": e}
        )

    # Validate password requirements
    valid_p, p_err = validate_password(p, username=u)
    if not valid_p:
        if is_json:
            return JSONResponse(status_code=400, content={"detail": p_err, "success": False})
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": p_err, "mode": "signup", "username": u, "email": e}
        )

    # Restrict self-signup to devops or viewer (admin requires explicit promotion)
    norm_r = normalize_role(r)
    assigned_role = norm_r if norm_r in ["devops", "viewer"] else "viewer"

    # Create the active user in database
    create_user(u, password=p, auth_type="local", email=e, role=assigned_role, is_active=True)

    record_audit_log(
        operator=u,
        role=assigned_role,
        action="USER_SIGNUP",
        details=f"New user registered with role '{assigned_role}'",
        target="auth"
    )

    if is_json:
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "message": f"Account created successfully for '{u}' (Role: {get_role_badge_label(assigned_role)})! Please sign in.",
                "username": u,
                "role": assigned_role
            }
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "success": f"Account created successfully for '{u}' (Role: {get_role_badge_label(assigned_role)})! Please sign in.",
            "mode": "login",
            "username": u
        }
    )


@router.get("/logout")
def logout(request: Request, response: Response):
    user_session = get_current_user_session(request)
    if user_session:
        record_audit_log(
            operator=user_session.username,
            role=user_session.role,
            action="USER_LOGOUT",
            details="User logged out of active session",
            target="auth"
        )
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
        return JSONResponse(status_code=400, content={"success": False, "error": "Please enter your Google email address."})

    is_valid, err_msg = verify_email_exists(email)
    if not is_valid:
        return JSONResponse(status_code=400, content={"success": False, "error": err_msg})

    clean_email = email.lower().strip()
    code, expires_at = create_verification_record(clean_email)
    res_tuple = send_verification_email(clean_email, code)
    if len(res_tuple) == 3:
        sent, delivery_msg, delivered_via_smtp = res_tuple
    else:
        sent, delivery_msg = res_tuple
        delivered_via_smtp = False

    if not sent:
        return JSONResponse(status_code=400, content={"success": False, "error": delivery_msg})

    parts = clean_email.split("@")
    local_part = parts[0]
    domain_part = parts[1]
    masked = f"{local_part[0]}***@{domain_part}" if len(local_part) <= 3 else f"{local_part[:2]}***{local_part[-2:]}@{domain_part}"

    return JSONResponse(content={
        "success": True,
        "message": f"A 6-digit confirmation code has been sent to {clean_email}." if delivered_via_smtp else f"Verification code generated for {clean_email}.",
        "email": clean_email,
        "masked_email": masked,
        "delivered_via_smtp": delivered_via_smtp,
        "expires_in_seconds": 600
    })


@router.post("/auth/oauth/google/verify-code")
async def google_verify_code(request: Request, response: Response):
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
        return JSONResponse(status_code=400, content={"success": False, "error": "Invalid request payload."})

    if not email or not code:
        return JSONResponse(status_code=400, content={"success": False, "error": "Email address and 6-digit code are required."})

    is_valid, err_msg = verify_email_code(email, code)
    if not is_valid:
        return JSONResponse(status_code=400, content={"success": False, "error": err_msg})

    username = email.split("@")[0].replace(".", "_").lower()
    existing_user = find_user(username)
    user_role = existing_user.get("role") if existing_user else USER_ROLES.get(username, "viewer")

    create_user(username, auth_type="google", email=email, role=user_role, is_active=True)
    token, max_age = create_session(username, role=user_role, remember_me=True, provider="google")

    record_audit_log(
        operator=username,
        role=user_role,
        action="OAUTH_LOGIN",
        details=f"Google 2-Step OTP verified for {email}",
        target="auth"
    )

    res = JSONResponse(content={
        "success": True,
        "message": "Account verified successfully! Logging you in...",
        "redirect_url": "/dashboard",
        "username": username,
        "role": user_role,
        "permissions": get_role_permissions(user_role),
        "email": email
    })
    res.set_cookie(key="session_token", value=token, max_age=max_age, httponly=True, samesite="lax", path="/")
    return res


@router.post("/auth/oauth/prompt-submit")
async def oauth_prompt_submit(
    request: Request,
    provider: Optional[str] = Form(None),
    account_input: Optional[str] = Form(None)
):
    try:
        content_type = request.headers.get("content-type", "")
        if (not provider or not account_input) and "application/json" in content_type:
            data = await request.json()
            if isinstance(data, dict):
                provider = provider or data.get("provider")
                account_input = account_input or data.get("account_input")
    except Exception:
        pass

    p = (provider or "").lower().strip()
    raw_acc = (account_input or "").strip()

    if not raw_acc:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": f"Please enter your {p.capitalize() if p else 'account'} details.", "mode": "login"}
        )

    if p == "google":
        email = raw_acc if "@" in raw_acc else f"{raw_acc}@gmail.com"
        username = email.split("@")[0].replace(".", "_").lower()
        auth_type = "google"
    elif p == "github":
        username = raw_acc.split("@")[0].replace(" ", "_").lower()
        email = raw_acc if "@" in raw_acc else f"{username}@github.local"
        auth_type = "github"
    else:
        username = raw_acc.replace(" ", "_").lower()
        email = f"{username}@predictops.local"
        auth_type = "oauth_demo"

    existing = find_user(username)
    user_role = existing.get("role") if existing else USER_ROLES.get(username, "viewer")

    create_user(username, auth_type=auth_type, email=email, role=user_role, is_active=True)
    token, max_age = create_session(username, role=user_role, remember_me=True, provider=auth_type)

    record_audit_log(
        operator=username,
        role=user_role,
        action="OAUTH_LOGIN",
        details=f"OAuth login completed via {auth_type}",
        target="auth"
    )

    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(key="session_token", value=token, max_age=max_age, httponly=True, samesite="lax", path="/")
    return redirect


@router.get("/auth/oauth/sandbox")
@router.get("/auth/oauth/demo")
def oauth_instant_disabled():
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@router.get("/auth/oauth/google/callback")
async def oauth_google_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    if error or not code:
        return RedirectResponse(url="/login?error=google_auth_failed", status_code=status.HTTP_302_FOUND)

    profile = await handle_google_callback(code)
    if not profile:
        return RedirectResponse(url="/login?error=google_profile_fetch_failed", status_code=status.HTTP_302_FOUND)

    username = profile["username"]
    existing = find_user(username)
    user_role = existing.get("role") if existing else USER_ROLES.get(username, "viewer")

    create_user(username, auth_type="google", email=profile.get("email"), role=user_role, is_active=True)
    token, max_age = create_session(username, role=user_role, remember_me=True, provider="google")

    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(key="session_token", value=token, max_age=max_age, httponly=True, samesite="lax", path="/")
    return redirect


@router.get("/auth/oauth/github/callback")
async def oauth_github_callback(request: Request, code: Optional[str] = None, error: Optional[str] = None):
    if error or not code:
        return RedirectResponse(url="/login?error=github_auth_failed", status_code=status.HTTP_302_FOUND)

    profile = await handle_github_callback(code)
    if not profile:
        return RedirectResponse(url="/login?error=github_profile_fetch_failed", status_code=status.HTTP_302_FOUND)

    username = profile["username"]
    existing = find_user(username)
    user_role = existing.get("role") if existing else USER_ROLES.get(username, "viewer")

    create_user(username, auth_type="github", email=profile.get("email"), role=user_role, is_active=True)
    token, max_age = create_session(username, role=user_role, remember_me=True, provider="github")

    redirect = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(key="session_token", value=token, max_age=max_age, httponly=True, samesite="lax", path="/")
    return redirect


@router.get("/auth/oauth/google")
@router.get("/auth/google-login")
def google_login_page():
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


@router.get("/auth/oauth/{provider}")
def oauth_authorize(provider: str):
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)


# =========================================================================
# RBAC Protected Alert Triage & Incident Workflow Endpoints
# =========================================================================

@router.post("/alerts/{alert_id}/acknowledge")
@router.post("/api/alerts/acknowledge")
async def acknowledge_alert_api(
    request: Request,
    alert_id: Optional[str] = None,
    operator: UserSession = Depends(require_permission("alerts.acknowledge"))
):
    """
    [DevOps & Admin] Triages and acknowledges an active anomaly alert.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    server_name = (alert_id or body.get("server_name") or "").strip()
    note = (body.get("note") or "").strip()

    if not server_name:
        return JSONResponse(status_code=400, content={"success": False, "detail": "Server name or alert ID is required."})

    res = record_incident_action(
        server_name=server_name,
        action="acknowledge",
        operator=operator.username,
        role=operator.role,
        note=note or f"Alert acknowledged by {operator.username} ({operator.role_badge})"
    )

    return {
        "success": True,
        "message": f"Alert on {server_name} acknowledged successfully.",
        "status": "ACKNOWLEDGED",
        "incident": res
    }


@router.post("/alerts/{alert_id}/resolve")
@router.post("/api/alerts/resolve")
async def resolve_alert_api(
    request: Request,
    alert_id: Optional[str] = None,
    operator: UserSession = Depends(require_permission("alerts.resolve"))
):
    """
    [DevOps & Admin] Marks an active anomaly alert as resolved.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    server_name = (alert_id or body.get("server_name") or "").strip()
    note = (body.get("note") or "").strip()

    if not server_name:
        return JSONResponse(status_code=400, content={"success": False, "detail": "Server name or alert ID is required."})

    res = record_incident_action(
        server_name=server_name,
        action="resolve",
        operator=operator.username,
        role=operator.role,
        note=note or f"Alert resolved by {operator.username} ({operator.role_badge})"
    )

    return {
        "success": True,
        "message": f"Alert on {server_name} marked as RESOLVED.",
        "status": "RESOLVED",
        "incident": res
    }


@router.post("/alerts/{alert_id}/override")
@router.post("/api/alerts/override")
async def override_alert_api(
    request: Request,
    alert_id: Optional[str] = None,
    admin_user: UserSession = Depends(require_permission("alerts.override"))
):
    """
    [Admin Only] Overrides and suppresses an active anomaly alert.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    server_name = (alert_id or body.get("server_name") or "").strip()
    reason = (body.get("reason") or body.get("note") or "Administrative manual suppression").strip()

    if not server_name:
        return JSONResponse(status_code=400, content={"success": False, "detail": "Server name or alert ID is required."})

    res = record_incident_action(
        server_name=server_name,
        action="override",
        operator=admin_user.username,
        role=admin_user.role,
        note=f"ADMIN OVERRIDE: {reason}"
    )

    record_audit_log(
        operator=admin_user.username,
        role=admin_user.role,
        action="ALERT_OVERRIDE",
        details=f"Admin overrode alert on {server_name}: {reason}",
        target=server_name
    )

    return {
        "success": True,
        "message": f"Alert on {server_name} overridden by Administrator.",
        "status": "OVERRIDDEN",
        "incident": res
    }


@router.get("/api/alerts/incident-actions")
def get_incident_actions_api(user_session: UserSession = Depends(require_permission("alerts.read"))):
    """
    Retrieves all active incident triage states for alerts.
    """
    actions = get_all_incident_actions()
    return {
        "success": True,
        "incident_actions": actions,
        "current_user_role": user_session.role,
        "permissions": user_session.permissions
    }


# =========================================================================
# RBAC Protected ML Operations Endpoints
# =========================================================================

@router.post("/ml/diagnostics")
@router.post("/api/ml/diagnostics")
def ml_diagnostics_api(operator: UserSession = Depends(require_permission("ml.diagnostics"))):
    """
    [DevOps & Admin] Executes manual inference diagnostics on the active ML anomaly model.
    """
    diag_res = run_ml_diagnostics()

    record_audit_log(
        operator=operator.username,
        role=operator.role,
        action="ML_DIAGNOSTICS",
        details=f"Inference diagnostics completed. Status: {diag_res.get('diagnostics_status', 'UNKNOWN')}",
        target="ml_model"
    )

    return {
        "success": True,
        "diagnostics": diag_res,
        "executed_by": operator.username
    }


@router.post("/ml/retrain")
@router.post("/api/ml/retrain")
def ml_retrain_api(admin_user: UserSession = Depends(require_permission("ml.retrain"))):
    """
    [Admin Only] Triggers full ML model retraining pipeline and updates active model.
    """
    retrain_res = trigger_ml_retrain()

    record_audit_log(
        operator=admin_user.username,
        role=admin_user.role,
        action="ML_RETRAIN",
        details=f"Full model retraining executed. Result: {retrain_res.get('message', 'Completed')}",
        target="ml_model"
    )

    return {
        "success": retrain_res.get("success", False),
        "result": retrain_res,
        "triggered_by": admin_user.username
    }


@router.post("/ml/hot-reload")
@router.post("/api/ml/hot-reload")
def ml_hot_reload_api(admin_user: UserSession = Depends(require_permission("ml.hot_reload"))):
    """
    [Admin Only] Hot-reloads the ML model binary into prediction service without server restart.
    """
    reload_res = hot_reload_model()

    record_audit_log(
        operator=admin_user.username,
        role=admin_user.role,
        action="ML_HOT_RELOAD",
        details=f"ML Model hot-reloaded from disk. Message: {reload_res.get('message', 'Done')}",
        target="ml_model"
    )

    return {
        "success": reload_res.get("success", False),
        "result": reload_res,
        "triggered_by": admin_user.username
    }


# =========================================================================
# RBAC Protected Cache & Simulator Endpoints
# =========================================================================

@router.post("/cache/flush")
@router.post("/api/cache/flush")
@router.post("/api/admin/cache/flush")
def flush_cache_api(operator: UserSession = Depends(require_permission("cache.flush"))):
    """
    [DevOps & Admin] Flushes all application memory and distributed caches.
    """
    stats_before = CacheService.get_stats()
    CacheService.clear_all()

    record_audit_log(
        operator=operator.username,
        role=operator.role,
        action="CACHE_FLUSH",
        details=f"Flushed cache tiers (Total keys purged: {stats_before.get('total_keys', 0)})",
        target="cache_service"
    )

    return {
        "success": True,
        "message": "All PredictOps AI memory caches have been flushed successfully.",
        "stats_purged": stats_before,
        "flushed_by": operator.username
    }


@router.post("/simulator/trigger")
@router.post("/api/simulator/trigger")
@router.post("/api/admin/simulate-spike")
async def simulate_spike_api(
    request: Request,
    operator: UserSession = Depends(require_permission("simulator.trigger"))
):
    """
    [DevOps & Admin] Injects a live chaos anomaly spike into server telemetry.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    server_name = (body.get("server_name") or "US-east-01").strip()
    metric_type = (body.get("metric") or "cpu").strip().lower()
    value = body.get("value")

    if value is not None:
        try:
            value = float(value)
        except Exception:
            value = None

    spike_res = inject_chaos_telemetry_spike(
        server_name=server_name,
        metric_type=metric_type,
        custom_value=value,
        injected_by=operator.username
    )

    record_audit_log(
        operator=operator.username,
        role=operator.role,
        action="SIMULATOR_TRIGGER",
        details=f"Injected {metric_type.upper()} anomaly spike onto server {server_name}",
        target=server_name
    )

    return {
        "success": True,
        "message": f"Chaos {metric_type.upper()} spike injected onto {server_name} successfully.",
        "details": spike_res
    }


@router.post("/simulator/full-control")
@router.post("/api/simulator/full-control")
async def simulator_full_control_api(
    request: Request,
    admin_user: UserSession = Depends(require_permission("simulator.full_control"))
):
    """
    [Admin Only] Full multi-server chaos generator and telemetry simulator control.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    servers = body.get("servers", ["US-east-01", "AUTH-server-01"])
    metric_type = (body.get("metric") or "cpu").strip().lower()
    results = []

    for s in servers:
        res = inject_chaos_telemetry_spike(server_name=s, metric_type=metric_type, injected_by=admin_user.username)
        results.append(res)

    record_audit_log(
        operator=admin_user.username,
        role=admin_user.role,
        action="SIMULATOR_FULL_CONTROL",
        details=f"Admin initiated multi-server chaos sweep on {len(servers)} nodes",
        target="simulator"
    )

    return {
        "success": True,
        "message": f"Full chaos wave injected across {len(servers)} servers.",
        "results": results
    }


# =========================================================================
# RBAC Protected Admin User & Role Management Endpoints
# =========================================================================

@router.get("/admin/users/list")
@router.get("/api/admin/users")
def get_all_users_api(admin_user: UserSession = Depends(require_permission("users.read"))):
    """
    [Admin Only] Retrieves all system user accounts with status, email, and role.
    """
    col = get_users_collection()
    user_list = []
    seen = set()

    if col is not None:
        try:
            cursor = col.find({}, {"password": 0, "password_hash": 0})
            for u in cursor:
                uname = u.get("username")
                if uname and uname not in seen:
                    seen.add(uname)
                    uid = str(u.get("_id", uname))
                    urole = normalize_role(u.get("role", "viewer"))
                    user_list.append({
                        "id": uid,
                        "username": uname,
                        "role": urole,
                        "role_badge": get_role_badge_label(urole),
                        "role_display": get_role_display_name(urole),
                        "email": u.get("email", f"{uname}@predictops.local"),
                        "is_active": u.get("is_active", True),
                        "auth_type": u.get("auth_type", "local"),
                        "created_at": u.get("created_at", "System Initialized")
                    })
        except Exception as e:
            logger.error(f"Error reading users from MongoDB: {e}")

    # Fallback memory users
    for uname, default_role in USER_ROLES.items():
        if uname not in seen:
            seen.add(uname)
            clean_r = normalize_role(default_role)
            user_list.append({
                "id": uname,
                "username": uname,
                "role": clean_r,
                "role_badge": get_role_badge_label(clean_r),
                "role_display": get_role_display_name(clean_r),
                "email": f"{uname}@predictops.local",
                "is_active": USER_STATUS.get(uname, True),
                "auth_type": "local",
                "created_at": "System Initialized"
            })

    return {
        "success": True,
        "users": user_list,
        "total_users": len(user_list),
        "requested_by": admin_user.username
    }


@router.post("/admin/users")
@router.post("/api/admin/users")
async def create_user_by_admin_api(
    request: Request,
    admin_user: UserSession = Depends(require_permission("users.create"))
):
    """
    [Admin Only] Provisions a new user account with specific role and active status.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    uname = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip()
    pwd = (body.get("password") or "").strip()
    role = normalize_role(body.get("role") or "viewer")
    is_active = bool(body.get("is_active", True))

    if not uname or not pwd or not email:
        return JSONResponse(status_code=400, content={"success": False, "detail": "Username, email, and password are required."})

    valid_u, u_err = validate_username(uname)
    if not valid_u:
        return JSONResponse(status_code=400, content={"success": False, "detail": u_err})

    valid_e, e_err = validate_email(email)
    if not valid_e:
        return JSONResponse(status_code=400, content={"success": False, "detail": e_err})

    if find_user(uname) is not None:
        return JSONResponse(status_code=400, content={"success": False, "detail": f"Username '{uname}' already exists."})

    valid_p, p_err = validate_password(pwd, username=uname)
    if not valid_p:
        return JSONResponse(status_code=400, content={"success": False, "detail": p_err})

    create_user(uname, password=pwd, auth_type="local", email=email, role=role, is_active=is_active)

    record_audit_log(
        operator=admin_user.username,
        role=admin_user.role,
        action="USER_CREATED",
        details=f"Admin created account '{uname}' with role '{role.upper()}' (Active: {is_active})",
        target=uname
    )

    return {
        "success": True,
        "message": f"User '{uname}' created successfully with role '{get_role_badge_label(role)}'.",
        "username": uname,
        "role": role,
        "is_active": is_active
    }


@router.patch("/admin/users/{user_id}/role")
@router.post("/api/admin/users/update-role")
async def update_user_role_api(
    request: Request,
    user_id: Optional[str] = None,
    admin_user: UserSession = Depends(require_permission("users.assign_role"))
):
    """
    [Admin Only] Updates a user's assigned role across database and active sessions.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    target = (user_id or body.get("username") or body.get("id") or "").strip()
    new_role = normalize_role(body.get("role") or "")

    if not target or not new_role:
        return JSONResponse(status_code=400, content={"success": False, "detail": "Target user and new role are required."})

    if new_role not in VALID_ROLES:
        return JSONResponse(status_code=400, content={"success": False, "detail": f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}"})

    user_doc = find_user(target)
    if not user_doc:
        return JSONResponse(status_code=404, content={"success": False, "detail": f"User '{target}' not found."})

    target_username = user_doc["username"]

    # Prevent admin self-demotion lockout
    if target_username == admin_user.username and new_role != "admin":
        return JSONResponse(status_code=400, content={"success": False, "detail": "You cannot demote your own admin account."})

    old_role = user_doc.get("role", "viewer")

    # Update in MongoDB
    col = get_users_collection()
    if col is not None:
        try:
            col.update_one(
                {"username": target_username},
                {"$set": {"role": new_role, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        except Exception as e:
            logger.error(f"Error updating role in MongoDB: {e}")

    USER_ROLES[target_username] = new_role

    # Update active sessions in memory immediately
    for token, sdata in list(ACTIVE_SESSIONS.items()):
        if sdata.get("username") == target_username:
            sdata["role"] = new_role

    record_audit_log(
        operator=admin_user.username,
        role=admin_user.role,
        action="USER_ROLE_UPDATED",
        details=f"Changed role of '{target_username}' from '{old_role}' to '{new_role}'",
        target=target_username
    )

    return {
        "success": True,
        "message": f"Successfully updated role for '{target_username}' to '{get_role_badge_label(new_role)}'.",
        "username": target_username,
        "new_role": new_role,
        "role_badge": get_role_badge_label(new_role)
    }


@router.post("/admin/users/{user_id}/deactivate")
@router.post("/api/admin/users/deactivate")
async def deactivate_user_api(
    request: Request,
    user_id: Optional[str] = None,
    admin_user: UserSession = Depends(require_permission("users.deactivate"))
):
    """
    [Admin Only] Deactivates a user account and terminates all active sessions.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    target = (user_id or body.get("username") or body.get("id") or "").strip()
    if not target:
        return JSONResponse(status_code=400, content={"success": False, "detail": "Target user is required."})

    user_doc = find_user(target)
    if not user_doc:
        return JSONResponse(status_code=404, content={"success": False, "detail": f"User '{target}' not found."})

    target_username = user_doc["username"]

    # Prevent admin self-deactivation lockout
    if target_username == admin_user.username:
        return JSONResponse(status_code=400, content={"success": False, "detail": "You cannot deactivate your own admin account."})

    col = get_users_collection()
    if col is not None:
        try:
            col.update_one(
                {"username": target_username},
                {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        except Exception as e:
            logger.error(f"Error deactivating user in MongoDB: {e}")

    USER_STATUS[target_username] = False

    # Invalidate all active sessions for this user immediately
    purge_user_sessions(target_username)

    record_audit_log(
        operator=admin_user.username,
        role=admin_user.role,
        action="USER_DEACTIVATED",
        details=f"Admin deactivated user account '{target_username}' and revoked all active sessions",
        target=target_username
    )

    return {
        "success": True,
        "message": f"User '{target_username}' has been deactivated.",
        "username": target_username,
        "is_active": False
    }


@router.post("/admin/users/{user_id}/activate")
@router.post("/api/admin/users/activate")
async def activate_user_api(
    request: Request,
    user_id: Optional[str] = None,
    admin_user: UserSession = Depends(require_permission("users.deactivate"))
):
    """
    [Admin Only] Re-activates a deactivated user account.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    target = (user_id or body.get("username") or body.get("id") or "").strip()
    if not target:
        return JSONResponse(status_code=400, content={"success": False, "detail": "Target user is required."})

    user_doc = find_user(target)
    if not user_doc:
        return JSONResponse(status_code=404, content={"success": False, "detail": f"User '{target}' not found."})

    target_username = user_doc["username"]

    col = get_users_collection()
    if col is not None:
        try:
            col.update_one(
                {"username": target_username},
                {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
        except Exception as e:
            logger.error(f"Error activating user in MongoDB: {e}")

    USER_STATUS[target_username] = True

    record_audit_log(
        operator=admin_user.username,
        role=admin_user.role,
        action="USER_ACTIVATED",
        details=f"Admin re-activated user account '{target_username}'",
        target=target_username
    )

    return {
        "success": True,
        "message": f"User '{target_username}' has been re-activated.",
        "username": target_username,
        "is_active": True
    }


@router.get("/api/admin/audit-logs")
def get_audit_logs_api(
    limit: int = Query(50, ge=1, le=200),
    admin_user: UserSession = Depends(require_permission("users.read"))
):
    """
    [Admin Only] Retrieves the operational and security audit log trail.
    """
    logs = get_recent_audit_logs(limit=limit)
    return {
        "success": True,
        "audit_logs": logs,
        "count": len(logs)
    }
