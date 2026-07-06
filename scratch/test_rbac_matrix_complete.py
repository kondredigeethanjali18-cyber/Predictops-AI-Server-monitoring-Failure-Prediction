import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure Backend is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Backend.main import app
from Backend.services.rbac_service import (
    ROLES,
    VIEWER_PERMISSIONS,
    DEVOPS_PERMISSIONS,
    ADMIN_PERMISSIONS,
    normalize_role,
    get_role_permissions,
    has_permission,
    get_role_badge_label,
    get_role_display_name
)
from Backend.services.session_service import create_session, destroy_session, purge_user_sessions
from Backend.routes.auth import create_user, USERS, USER_ROLES, USER_STATUS


def test_rbac_service_definitions():
    """Verify role definitions and exact permission sets."""
    assert normalize_role("viewer") == "viewer"
    assert normalize_role("analyst") == "viewer"
    assert normalize_role("devops") == "devops"
    assert normalize_role("engineer") == "devops"
    assert normalize_role("admin") == "admin"
    assert normalize_role("superadmin") == "admin"

    # Viewer permissions check
    v_perms = get_role_permissions("viewer")
    assert "dashboard.read" in v_perms
    assert "telemetry.read" in v_perms
    assert "analytics.read" in v_perms
    assert "predictions.read" in v_perms
    assert "alerts.read" in v_perms
    assert "alerts.acknowledge" not in v_perms
    assert "ml.diagnostics" not in v_perms
    assert "users.read" not in v_perms

    # DevOps permissions check
    d_perms = get_role_permissions("devops")
    assert "alerts.acknowledge" in d_perms
    assert "alerts.resolve" in d_perms
    assert "ml.diagnostics" in d_perms
    assert "cache.flush" in d_perms
    assert "simulator.trigger" in d_perms
    assert "alerts.override" not in d_perms
    assert "ml.retrain" not in d_perms
    assert "users.create" not in d_perms

    # Admin permissions check
    a_perms = get_role_permissions("admin")
    assert "alerts.override" in a_perms
    assert "ml.retrain" in a_perms
    assert "ml.hot_reload" in a_perms
    assert "simulator.full_control" in a_perms
    assert "users.read" in a_perms
    assert "users.create" in a_perms
    assert "users.assign_role" in a_perms
    assert "users.deactivate" in a_perms

    # Display names & badges
    assert get_role_badge_label("admin") == "ADMIN"
    assert get_role_badge_label("devops") == "DEVOPS ENGINEER"
    assert get_role_badge_label("viewer") == "VIEWER"


def test_unauthenticated_requests_rejected():
    """Unauthenticated requests must be rejected with 401 (API) or 302 (HTML)."""
    client = TestClient(app)

    # API endpoints -> 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/alerts/acknowledge", json={"server_name": "US-east-01"}).status_code == 401
    assert client.post("/api/ml/diagnostics").status_code == 401
    assert client.post("/api/cache/flush").status_code == 401
    assert client.get("/api/admin/users").status_code == 401

    # Page endpoints with HTML accept header -> 302 Redirect to /login
    html_headers = {"Accept": "text/html"}
    assert client.get("/dashboard", headers=html_headers, follow_redirects=False).status_code == 302
    assert client.get("/admin", headers=html_headers, follow_redirects=False).status_code == 302
    assert client.get("/admin/users", headers=html_headers, follow_redirects=False).status_code == 302


def test_viewer_role_access_matrix():
    """Test viewer role permissions: read allowed, all write/ops/admin forbidden (403)."""
    client = TestClient(app)
    create_user("test_viewer", "ViewerPass123!", email="viewer@test.com", role="viewer", is_active=True)
    token, _ = create_session("test_viewer", role="viewer")
    headers = {"Authorization": f"Bearer {token}"}
    cookies = {"session_token": token}

    # 1. /auth/me returns viewer info
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "viewer"
    assert data["role_badge"] == "VIEWER"
    assert "dashboard.read" in data["permissions"]
    assert "alerts.acknowledge" not in data["permissions"]

    # 2. Read pages and data allowed
    assert client.get("/dashboard", cookies=cookies).status_code == 200
    assert client.get("/servers", cookies=cookies).status_code == 200
    assert client.get("/predictions", cookies=cookies).status_code == 200
    assert client.get("/alerts", cookies=cookies).status_code == 200
    assert client.get("/insights", cookies=cookies).status_code == 200
    assert client.get("/analytics", cookies=cookies).status_code == 200

    # 3. Alert triage -> 403 Forbidden
    assert client.post("/alerts/US-east-01/acknowledge", headers=headers, json={"server_name": "US-east-01"}).status_code == 403
    assert client.post("/alerts/US-east-01/resolve", headers=headers, json={"server_name": "US-east-01"}).status_code == 403
    assert client.post("/alerts/US-east-01/override", headers=headers, json={"server_name": "US-east-01"}).status_code == 403

    # 4. ML operations -> 403 Forbidden
    assert client.post("/api/ml/diagnostics", headers=headers).status_code == 403
    assert client.post("/api/ml/retrain", headers=headers).status_code == 403
    assert client.post("/api/ml/hot-reload", headers=headers).status_code == 403

    # 5. Cache / Simulator -> 403 Forbidden
    assert client.post("/api/cache/flush", headers=headers).status_code == 403
    assert client.post("/api/simulator/trigger", headers=headers, json={"server_name": "US-east-01"}).status_code == 403
    assert client.post("/api/simulator/full-control", headers=headers).status_code == 403

    # 6. Admin User Management -> 403 Forbidden
    assert client.get("/api/admin/users", headers=headers).status_code == 403
    assert client.post("/api/admin/users", headers=headers, json={"username": "new", "email": "n@n.com", "password": "p"}).status_code == 403
    assert client.get("/admin/users", cookies=cookies).status_code == 403
    assert client.get("/admin", cookies=cookies).status_code == 403


def test_devops_role_access_matrix():
    """Test DevOps Engineer role permissions: read + triage + diagnostics + cache/sim allowed, admin ops forbidden (403)."""
    client = TestClient(app)
    create_user("test_devops", "DevopsPass123!", email="devops@test.com", role="devops", is_active=True)
    token, _ = create_session("test_devops", role="devops")
    headers = {"Authorization": f"Bearer {token}"}
    cookies = {"session_token": token}

    # 1. /auth/me returns devops info
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "devops"
    assert data["role_badge"] == "DEVOPS ENGINEER"
    assert "alerts.acknowledge" in data["permissions"]
    assert "ml.diagnostics" in data["permissions"]
    assert "ml.retrain" not in data["permissions"]
    assert "alerts.override" not in data["permissions"]

    # 2. Read pages allowed
    assert client.get("/dashboard", cookies=cookies).status_code == 200
    assert client.get("/alerts", cookies=cookies).status_code == 200

    # 3. Alert acknowledge & resolve -> 200 OK
    ack_res = client.post("/alerts/US-east-01/acknowledge", headers=headers, json={"server_name": "US-east-01", "note": "Checked logs"})
    assert ack_res.status_code == 200
    assert ack_res.json()["success"] is True

    res_res = client.post("/alerts/US-east-01/resolve", headers=headers, json={"server_name": "US-east-01", "note": "Pods scaled"})
    assert res_res.status_code == 200
    assert res_res.json()["success"] is True

    # 4. Alert override -> 403 Forbidden (Admin only)
    assert client.post("/alerts/US-east-01/override", headers=headers, json={"server_name": "US-east-01"}).status_code == 403

    # 5. ML diagnostics -> 200 OK
    diag_res = client.post("/api/ml/diagnostics", headers=headers)
    assert diag_res.status_code == 200
    assert diag_res.json()["success"] is True

    # 6. ML retrain & hot-reload -> 403 Forbidden (Admin only)
    assert client.post("/api/ml/retrain", headers=headers).status_code == 403
    assert client.post("/api/ml/hot-reload", headers=headers).status_code == 403

    # 7. Cache flush & Simulator trigger -> 200 OK
    assert client.post("/api/cache/flush", headers=headers).status_code == 200
    assert client.post("/api/simulator/trigger", headers=headers, json={"server_name": "US-east-01", "metric": "cpu"}).status_code == 200

    # 8. Simulator full control & User Management -> 403 Forbidden (Admin only)
    assert client.post("/api/simulator/full-control", headers=headers).status_code == 403
    assert client.get("/api/admin/users", headers=headers).status_code == 403
    assert client.get("/admin/users", cookies=cookies).status_code == 403


def test_admin_role_access_matrix():
    """Test Admin role permissions: full access across all endpoints."""
    client = TestClient(app)
    create_user("test_admin", "AdminPass123!", email="admin@test.com", role="admin", is_active=True)
    token, _ = create_session("test_admin", role="admin")
    headers = {"Authorization": f"Bearer {token}"}
    cookies = {"session_token": token}

    # 1. /auth/me returns admin info
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert data["role_badge"] == "ADMIN"
    assert "users.read" in data["permissions"]
    assert "alerts.override" in data["permissions"]

    # 2. Pages & Console access
    assert client.get("/dashboard", cookies=cookies).status_code == 200
    assert client.get("/admin", cookies=cookies).status_code == 200
    assert client.get("/admin/users", cookies=cookies).status_code == 200

    # 3. Alert override -> 200 OK
    ov_res = client.post("/alerts/US-east-01/override", headers=headers, json={"server_name": "US-east-01", "reason": "Scheduled maintenance"})
    assert ov_res.status_code == 200
    assert ov_res.json()["success"] is True

    # 4. ML Retrain & Hot Reload -> 200 OK
    assert client.post("/api/ml/diagnostics", headers=headers).status_code == 200
    assert client.post("/api/ml/retrain", headers=headers).status_code == 200
    assert client.post("/api/ml/hot-reload", headers=headers).status_code == 200

    # 5. Cache Flush & Simulator Full Control -> 200 OK
    assert client.post("/api/cache/flush", headers=headers).status_code == 200
    assert client.post("/api/simulator/full-control", headers=headers, json={"servers": ["US-east-01"]}).status_code == 200

    # 6. Admin User Management CRUD -> 200 OK
    list_res = client.get("/api/admin/users", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["success"] is True

    # Create new user via admin API
    import uuid
    dynamic_user = f"sarah_{uuid.uuid4().hex[:6]}"
    create_res = client.post("/api/admin/users", headers=headers, json={
        "username": dynamic_user,
        "email": f"{dynamic_user}@predictops.com",
        "password": "SarahPass123!",
        "role": "viewer",
        "is_active": True
    })
    assert create_res.status_code == 200
    assert create_res.json()["success"] is True

    # Update role to devops
    role_res = client.patch(f"/admin/users/{dynamic_user}/role", headers=headers, json={"role": "devops"})
    assert role_res.status_code == 200
    assert role_res.json()["new_role"] == "devops"

    # Deactivate user
    deact_res = client.post(f"/admin/users/{dynamic_user}/deactivate", headers=headers)
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False

    # Deactivated user cannot login
    client_sarah = TestClient(app)
    login_attempt = client_sarah.post("/login", data={"username": dynamic_user, "password": "SarahPass123!"}, headers={"Accept": "application/json"})
    assert login_attempt.status_code == 401

    # Re-activate user
    act_res = client.post(f"/admin/users/{dynamic_user}/activate", headers=headers)
    assert act_res.status_code == 200
    assert act_res.json()["is_active"] is True

    # Re-activated user can now login
    login_ok = client_sarah.post("/login", data={"username": dynamic_user, "password": "SarahPass123!"}, headers={"Accept": "application/json"})
    assert login_ok.status_code == 200
    assert login_ok.json()["success"] is True


def test_admin_self_protection():
    """Admin cannot demote or deactivate their own active account."""
    client = TestClient(app)
    create_user("test_admin_protect", "AdminPass123!", email="adminprot@test.com", role="admin", is_active=True)
    token, _ = create_session("test_admin_protect", role="admin")
    headers = {"Authorization": f"Bearer {token}"}

    # Demotion attempt
    demote_res = client.patch("/admin/users/test_admin_protect/role", headers=headers, json={"role": "viewer"})
    assert demote_res.status_code == 400

    # Deactivation attempt
    deact_res = client.post("/admin/users/test_admin_protect/deactivate", headers=headers)
    assert deact_res.status_code == 400


if __name__ == "__main__":
    pytest.main(["-v", __file__])
