import os
import json
import urllib.parse
import urllib.request
import logging
import uuid
from typing import Optional, Dict, Any
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

# Environment Configuration
OAUTH_REDIRECT_BASE = os.getenv("OAUTH_REDIRECT_BASE_URL", "http://localhost:8000")

# Google OAuth 2.0 Settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# GitHub OAuth 2.0 Settings
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"


def get_google_auth_url(state: Optional[str] = None) -> str:
    """Generates the authorization URL for Google OAuth 2.0."""
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/auth/oauth/google/callback"
    state_val = state or str(uuid.uuid4())
    
    # If no live client ID is configured, route to developer sandbox flow
    if not GOOGLE_CLIENT_ID:
        return f"/auth/oauth/sandbox?provider=google&state={state_val}"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state_val,
        "prompt": "select_account"
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def get_github_auth_url(state: Optional[str] = None) -> str:
    """Generates the authorization URL for GitHub OAuth 2.0."""
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/auth/oauth/github/callback"
    state_val = state or str(uuid.uuid4())

    # If no live client ID is configured, route to developer sandbox flow
    if not GITHUB_CLIENT_ID:
        return f"/auth/oauth/sandbox?provider=github&state={state_val}"

    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "read:user user:email",
        "state": state_val
    }
    return f"{GITHUB_AUTH_URL}?{urllib.parse.urlencode(params)}"


def _http_post_form(url: str, data: dict, headers: dict = None) -> dict:
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded_data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_json(url: str, headers: dict = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def handle_google_callback(code: str) -> Optional[Dict[str, Any]]:
    """Exchanges Google authorization code for user profile."""
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/auth/oauth/google/callback"
    try:
        token_data = await run_in_threadpool(
            _http_post_form,
            GOOGLE_TOKEN_URL,
            {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            {"Accept": "application/json"}
        )
        access_token = token_data.get("access_token")

        if not access_token:
            logger.error(f"Failed to obtain Google access token: {token_data}")
            return None

        user_data = await run_in_threadpool(
            _http_get_json,
            GOOGLE_USERINFO_URL,
            {"Authorization": f"Bearer {access_token}"}
        )

        email = user_data.get("email", "")
        username = email.split("@")[0] if email else user_data.get("name", f"google_user_{uuid.uuid4().hex[:6]}")
        username = username.replace(" ", "_").lower()

        return {
            "provider": "google",
            "provider_id": user_data.get("id"),
            "email": email,
            "username": username,
            "display_name": user_data.get("name", username),
            "picture": user_data.get("picture", "")
        }
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return None


async def handle_github_callback(code: str) -> Optional[Dict[str, Any]]:
    """Exchanges GitHub authorization code for user profile."""
    redirect_uri = f"{OAUTH_REDIRECT_BASE}/auth/oauth/github/callback"
    try:
        token_data = await run_in_threadpool(
            _http_post_form,
            GITHUB_TOKEN_URL,
            {
                "code": code,
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
            },
            {"Accept": "application/json"}
        )
        access_token = token_data.get("access_token")

        if not access_token:
            logger.error(f"Failed to obtain GitHub access token: {token_data}")
            return None

        user_data = await run_in_threadpool(
            _http_get_json,
            GITHUB_USERINFO_URL,
            {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "User-Agent": "PredictOps-AI-OAuth"
            }
        )

        username = user_data.get("login") or f"github_user_{uuid.uuid4().hex[:6]}"
        email = user_data.get("email") or f"{username}@github.local"

        return {
            "provider": "github",
            "provider_id": str(user_data.get("id")),
            "email": email,
            "username": username,
            "display_name": user_data.get("name") or username,
            "picture": user_data.get("avatar_url", "")
        }
    except Exception as e:
        logger.error(f"GitHub OAuth callback error: {e}")
        return None


def get_sandbox_user(provider: str) -> Dict[str, Any]:
    """Generates an immediate verified user profile for developer sandbox testing."""
    if provider == "google":
        return {
            "provider": "google_sandbox",
            "provider_id": "sandbox_g_102938475",
            "email": "alex.morgan@predictops.ai",
            "username": "alex.google",
            "display_name": "Alex Morgan (Google OAuth)",
            "picture": ""
        }
    elif provider == "github":
        return {
            "provider": "github_sandbox",
            "provider_id": "sandbox_gh_594837261",
            "email": "devops.lead@github.local",
            "username": "devops_lead",
            "display_name": "DevOps Lead (GitHub OAuth)",
            "picture": ""
        }
    else:
        return {
            "provider": "demo_oauth",
            "provider_id": f"sandbox_demo_{uuid.uuid4().hex[:8]}",
            "email": "demo.engineer@predictops.ai",
            "username": "demo_engineer",
            "display_name": "Demo Infrastructure Engineer",
            "picture": ""
        }
