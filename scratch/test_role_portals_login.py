import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Backend.main import app
from Backend.routes.auth import create_user

client = TestClient(app)


def test_role_portals_login_matrix():
    # Setup test users for each role
    create_user("portal_admin", "AdminPass123!", email="p_admin@test.com", role="admin", is_active=True)
    create_user("portal_devops", "DevopsPass123!", email="p_devops@test.com", role="devops", is_active=True)
    create_user("portal_viewer", "ViewerPass123!", email="p_viewer@test.com", role="viewer", is_active=True)

    # 1. ADMIN PORTAL TESTS
    # Admin logging into Admin portal -> 200 Success & redirect to /admin
    c_admin = TestClient(app)
    resp = c_admin.post("/login", data={"username": "portal_admin", "password": "AdminPass123!", "login_portal": "admin"}, headers={"Accept": "application/json"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["role"] == "admin"
    assert data["redirect_url"] == "/admin"

    # DevOps trying to log into Admin portal -> 403 Forbidden
    c_devops = TestClient(app)
    resp = c_devops.post("/login", data={"username": "portal_devops", "password": "DevopsPass123!", "login_portal": "admin"}, headers={"Accept": "application/json"})
    assert resp.status_code == 403
    assert "not authorized for the Administrator Portal" in resp.json()["detail"]

    # Viewer trying to log into Admin portal -> 403 Forbidden
    c_viewer = TestClient(app)
    resp = c_viewer.post("/login", data={"username": "portal_viewer", "password": "ViewerPass123!", "login_portal": "admin"}, headers={"Accept": "application/json"})
    assert resp.status_code == 403
    assert "not authorized for the Administrator Portal" in resp.json()["detail"]

    # 2. DEVOPS PORTAL TESTS
    # DevOps logging into DevOps portal -> 200 Success
    resp = c_devops.post("/login", data={"username": "portal_devops", "password": "DevopsPass123!", "login_portal": "devops"}, headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "devops"

    # Admin logging into DevOps portal -> 200 Success (Admin has elevated permissions)
    resp = c_admin.post("/login", data={"username": "portal_admin", "password": "AdminPass123!", "login_portal": "devops"}, headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

    # Viewer trying to log into DevOps portal -> 403 Forbidden
    resp = c_viewer.post("/login", data={"username": "portal_viewer", "password": "ViewerPass123!", "login_portal": "devops"}, headers={"Accept": "application/json"})
    assert resp.status_code == 403
    assert "not authorized for the DevOps Engineer Portal" in resp.json()["detail"]

    # 3. VIEWER PORTAL TESTS
    # Viewer logging into Viewer portal -> 200 Success
    resp = c_viewer.post("/login", data={"username": "portal_viewer", "password": "ViewerPass123!", "login_portal": "viewer"}, headers={"Accept": "application/json"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"

    # DevOps logging into Viewer portal -> 200 Success
    resp = c_devops.post("/login", data={"username": "portal_devops", "password": "DevopsPass123!", "login_portal": "viewer"}, headers={"Accept": "application/json"})
    assert resp.status_code == 200

    # Admin logging into Viewer portal -> 200 Success
    resp = c_admin.post("/login", data={"username": "portal_admin", "password": "AdminPass123!", "login_portal": "viewer"}, headers={"Accept": "application/json"})
    assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main(["-v", __file__])
