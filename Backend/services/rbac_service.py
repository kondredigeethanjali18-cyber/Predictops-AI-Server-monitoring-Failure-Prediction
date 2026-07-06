"""
PredictOps AI - Role-Based Access Control (RBAC) Service
Defines application roles, exact permission sets, role hierarchies, and permission checking logic.
"""

from typing import List, Dict, Any, Optional

# =========================================================================
# System Permissions Definition
# =========================================================================

VIEWER_PERMISSIONS: List[str] = [
    "dashboard.read",
    "telemetry.read",
    "analytics.read",
    "predictions.read",
    "alerts.read"
]

DEVOPS_PERMISSIONS: List[str] = VIEWER_PERMISSIONS + [
    "alerts.acknowledge",
    "alerts.resolve",
    "ml.diagnostics",
    "cache.flush",
    "simulator.trigger"
]

ADMIN_PERMISSIONS: List[str] = DEVOPS_PERMISSIONS + [
    "alerts.override",
    "ml.retrain",
    "ml.hot_reload",
    "simulator.full_control",
    "users.read",
    "users.create",
    "users.assign_role",
    "users.deactivate"
]

# Central Roles and Permissions Configuration
ROLES: Dict[str, Dict[str, Any]] = {
    "viewer": {
        "id": "viewer",
        "name": "Viewer (Analyst)",
        "badge": "VIEWER",
        "permissions": list(VIEWER_PERMISSIONS)
    },
    "devops": {
        "id": "devops",
        "name": "DevOps Engineer (Operator)",
        "badge": "DEVOPS ENGINEER",
        "permissions": list(DEVOPS_PERMISSIONS)
    },
    "admin": {
        "id": "admin",
        "name": "Admin (Administrator)",
        "badge": "ADMIN",
        "permissions": list(ADMIN_PERMISSIONS)
    }
}

VALID_ROLES: List[str] = list(ROLES.keys())


def normalize_role(role_name: Optional[str]) -> str:
    """Normalizes legacy or alias role strings to stable internal identifiers ('viewer', 'devops', 'admin')."""
    if not role_name:
        return "viewer"
    r = str(role_name).strip().lower()
    if r in ("admin", "administrator", "superadmin"):
        return "admin"
    if r in ("devops", "engineer", "operator", "devops engineer"):
        return "devops"
    return "viewer"


def get_role_permissions(role: str) -> List[str]:
    """Retrieves list of permissions for a normalized role."""
    norm = normalize_role(role)
    return ROLES.get(norm, ROLES["viewer"])["permissions"]


def has_permission(user_role: str, permission: str) -> bool:
    """Checks whether a given role holds the requested permission identifier."""
    norm = normalize_role(user_role)
    role_perms = get_role_permissions(norm)
    return permission in role_perms


def has_any_permission(user_role: str, permissions: List[str]) -> bool:
    """Checks whether a role holds at least one of the requested permissions."""
    return any(has_permission(user_role, p) for p in permissions)


def get_role_badge_label(role: str) -> str:
    """Returns the visual badge label for a role."""
    norm = normalize_role(role)
    return ROLES.get(norm, ROLES["viewer"])["badge"]


def get_role_display_name(role: str) -> str:
    """Returns the user-facing display name for a role."""
    norm = normalize_role(role)
    return ROLES.get(norm, ROLES["viewer"])["name"]
