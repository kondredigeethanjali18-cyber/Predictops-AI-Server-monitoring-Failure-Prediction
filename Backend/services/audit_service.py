import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from Backend.database.mongodb import db

logger = logging.getLogger(__name__)

# In-memory circular buffer for fast audit retrieval
AUDIT_LOGS_MEMORY: List[Dict[str, Any]] = []
MAX_IN_MEMORY_LOGS = 200

# In-memory incident action cache: server_name -> action_dict
INCIDENT_ACTIONS_MEMORY: Dict[str, Dict[str, Any]] = {}


def get_audit_collection():
    if db is not None:
        try:
            return db["audit_logs"]
        except Exception as e:
            logger.warning(f"Error accessing audit_logs collection: {e}")
    return None


def get_incident_collection():
    if db is not None:
        try:
            return db["incident_actions"]
        except Exception as e:
            logger.warning(f"Error accessing incident_actions collection: {e}")
    return None


def format_ist_timestamp(dt: datetime) -> str:
    """Format datetime in IST (UTC+5:30)."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    ist_dt = dt.astimezone(ist_tz)
    return ist_dt.strftime("%d %b, %I:%M:%S %p (IST)")


def record_audit_log(operator: str, role: str, action: str, details: str, target: Optional[str] = None) -> Dict[str, Any]:
    """
    Records an operational or security event into the audit trail.
    """
    now = datetime.now(timezone.utc)
    entry = {
        "timestamp": now.isoformat(),
        "timestamp_ist": format_ist_timestamp(now),
        "operator": operator,
        "role": role,
        "action": action,
        "details": details,
        "target": target or "system"
    }

    # Prepend clean copy to in-memory list
    AUDIT_LOGS_MEMORY.insert(0, dict(entry))
    if len(AUDIT_LOGS_MEMORY) > MAX_IN_MEMORY_LOGS:
        AUDIT_LOGS_MEMORY.pop()

    # Save to MongoDB
    col = get_audit_collection()
    if col is not None:
        try:
            doc_to_save = dict(entry)
            col.insert_one(doc_to_save)
        except Exception as e:
            logger.error(f"Error writing audit log to MongoDB: {e}")

    logger.info(f"AUDIT LOG: [{entry['timestamp_ist']}] {operator} ({role}) - {action}: {details}")
    return entry


def get_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent audit logs from MongoDB or in-memory fallback."""
    col = get_audit_collection()
    if col is not None:
        try:
            cursor = col.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
            logs = []
            for doc in cursor:
                doc.pop("_id", None)
                logs.append(doc)
            if logs:
                return logs
        except Exception as e:
            logger.error(f"Error reading audit logs from MongoDB: {e}")

    clean_logs = []
    for item in AUDIT_LOGS_MEMORY[:limit]:
        c = dict(item)
        c.pop("_id", None)
        clean_logs.append(c)
    return clean_logs


def record_incident_action(server_name: str, action: str, operator: str, role: str, note: Optional[str] = None) -> Dict[str, Any]:
    """
    Records an incident triage action (e.g. acknowledge, resolve) for an active server anomaly.
    """
    now = datetime.now(timezone.utc)
    action_clean = action.lower().strip()
    status_text = "RESOLVED" if action_clean == "resolve" else "ACKNOWLEDGED"

    doc = {
        "server_name": server_name,
        "status": status_text,
        "action": action_clean,
        "operator": operator,
        "role": role,
        "note": note or f"Incident {action_clean}d by {operator}",
        "timestamp": now.isoformat(),
        "timestamp_ist": format_ist_timestamp(now),
        "updated_at": now.isoformat()
    }

    col = get_incident_collection()
    if col is not None:
        try:
            col.update_one(
                {"server_name": server_name},
                {"$set": doc},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving incident action to MongoDB: {e}")

    doc.pop("_id", None)
    INCIDENT_ACTIONS_MEMORY[server_name] = doc

    # Also log to audit trail
    record_audit_log(
        operator=operator,
        role=role,
        action=f"INCIDENT_{status_text}",
        details=f"{status_text} anomaly alert on {server_name}. Note: {doc['note']}",
        target=server_name
    )

    return doc


def get_all_incident_actions() -> Dict[str, Dict[str, Any]]:
    """Retrieves all active incident action statuses."""
    col = get_incident_collection()
    if col is not None:
        try:
            cursor = col.find({}, {"_id": 0})
            result = {}
            for item in cursor:
                sname = item.get("server_name")
                if sname:
                    result[sname] = item
                    INCIDENT_ACTIONS_MEMORY[sname] = item
            if result:
                return result
        except Exception as e:
            logger.error(f"Error loading incident actions from MongoDB: {e}")

    return dict(INCIDENT_ACTIONS_MEMORY)
