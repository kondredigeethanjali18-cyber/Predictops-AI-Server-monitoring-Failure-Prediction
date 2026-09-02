import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from Backend.database.mongodb import get_predictions_collection, db

logger = logging.getLogger(__name__)

# Default session duration: 24 hours. Remember-me session duration: 7 days.
DEFAULT_SESSION_HOURS = 24
REMEMBER_ME_DAYS = 7

# In-memory session cache: token -> session_dict
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_sessions_collection():
    """Retrieve MongoDB sessions collection dynamically."""
    if db is not None:
        try:
            col = db["sessions"]
            return col
        except Exception as e:
            logger.warning(f"Failed to get sessions collection from db: {e}")
    return None


def create_session(username: str, remember_me: bool = False, provider: str = "local") -> tuple[str, int]:
    """
    Creates a new session for a user.
    Returns: (session_token, max_age_in_seconds)
    """
    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    if remember_me:
        duration = timedelta(days=REMEMBER_ME_DAYS)
        max_age = REMEMBER_ME_DAYS * 24 * 3600
    else:
        duration = timedelta(hours=DEFAULT_SESSION_HOURS)
        max_age = DEFAULT_SESSION_HOURS * 3600

    expires_at = now + duration

    session_data = {
        "session_token": token,
        "username": username,
        "provider": provider,
        "remember_me": remember_me,
        "created_at": now.isoformat(),
        "last_active_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }

    # Store in-memory
    ACTIVE_SESSIONS[token] = session_data

    # Store in MongoDB
    col = get_sessions_collection()
    if col is not None:
        try:
            col.insert_one(dict(session_data))
        except Exception as e:
            logger.error(f"Error persisting session to MongoDB: {e}")

    logger.info(f"Created session for user '{username}' (provider: {provider}, remember_me: {remember_me})")
    return token, max_age


def validate_session(token: str) -> Optional[str]:
    """
    Validates a session token.
    Checks expiry, refreshes last_active timestamp (sliding window), and returns username if valid.
    """
    if not token:
        return None

    now = datetime.now(timezone.utc)
    session_data = ACTIVE_SESSIONS.get(token)

    # If not in memory, check MongoDB
    if not session_data:
        col = get_sessions_collection()
        if col is not None:
            try:
                doc = col.find_one({"session_token": token})
                if doc:
                    session_data = doc
                    ACTIVE_SESSIONS[token] = doc
            except Exception as e:
                logger.error(f"Error fetching session from MongoDB: {e}")

    if not session_data:
        return None

    # Check expiration
    expires_str = session_data.get("expires_at")
    if expires_str:
        try:
            expires_at = datetime.fromisoformat(expires_str)
            if now > expires_at:
                logger.info(f"Session expired for token {token[:8]}...")
                destroy_session(token)
                return None
        except Exception:
            pass

    # Sliding session renewal: update last_active_at
    session_data["last_active_at"] = now.isoformat()
    col = get_sessions_collection()
    if col is not None:
        try:
            col.update_one(
                {"session_token": token},
                {"$set": {"last_active_at": now.isoformat()}}
            )
        except Exception:
            pass

    return session_data.get("username")


def destroy_session(token: str):
    """Destroys an active session upon logout or expiration."""
    if not token:
        return

    if token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[token]

    col = get_sessions_collection()
    if col is not None:
        try:
            col.delete_one({"session_token": token})
        except Exception as e:
            logger.error(f"Error deleting session from MongoDB: {e}")

    logger.info(f"Session destroyed for token {token[:8]}...")


def purge_all_sessions():
    """Wipes all sessions (e.g. on application startup)."""
    ACTIVE_SESSIONS.clear()
    col = get_sessions_collection()
    if col is not None:
        try:
            col.delete_many({})
        except Exception as e:
            logger.error(f"Error purging sessions from MongoDB: {e}")
    logger.info("All active sessions purged successfully.")


def clean_expired_sessions():
    """Removes expired sessions from memory and MongoDB."""
    now = datetime.now(timezone.utc)
    expired_tokens = []

    for token, s in list(ACTIVE_SESSIONS.items()):
        exp = s.get("expires_at")
        if exp:
            try:
                if now > datetime.fromisoformat(exp):
                    expired_tokens.append(token)
            except Exception:
                pass

    for t in expired_tokens:
        destroy_session(t)

    col = get_sessions_collection()
    if col is not None:
        try:
            col.delete_many({"expires_at": {"$lt": now.isoformat()}})
        except Exception:
            pass
