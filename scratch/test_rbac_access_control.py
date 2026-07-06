import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Backend.main import app
from Backend.routes.auth import (
    create_user,
    find_user,
    seed_default_users,
    USER_ROLES
)
from Backend.services.session_service import create_session

client = TestClient(app, follow_redirects=False)

class TestPredictOpsRBAC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_default_users()

    def test_default_seeded_roles(self):
        """Verify default users vamsi and geethanjali have their respective roles."""
        vamsi = find_user("vamsi")
        self.assertIsNotNone(vamsi)
        self.assertEqual(vamsi.get("role"), "admin")

        geethanjali = find_user("geethanjali")
        self.assertIsNotNone(geethanjali)
        self.assertEqual(geethanjali.get("role"), "engineer")

    def test_viewer_access_restrictions_403(self):
        """Verify viewer role receives 403 Forbidden on administrative and operator endpoints."""
        # Create viewer user session
        create_user("test_viewer_01", password="TestPassword123!", role="viewer")
        token, _ = create_session("test_viewer_01", role="viewer")
        cookies = {"session_token": token}

        # 1. Admin users list - Expect 403
        res = client.get("/api/admin/users", cookies=cookies)
        self.assertEqual(res.status_code, 403)

        # 2. Cache flush - Expect 403
        res = client.post("/api/admin/cache/flush", cookies=cookies)
        self.assertEqual(res.status_code, 403)

        # 3. Chaos spike simulation - Expect 403
        res = client.post("/api/admin/simulate-spike", json={"server_name": "US-east-01", "metric": "cpu"}, cookies=cookies)
        self.assertEqual(res.status_code, 403)

        # 4. Audit logs - Expect 403
        res = client.get("/api/admin/audit-logs", cookies=cookies)
        self.assertEqual(res.status_code, 403)

        # 5. Alert triage acknowledge - Expect 403
        res = client.post("/api/alerts/acknowledge", json={"server_name": "US-east-01", "action": "acknowledge"}, cookies=cookies)
        self.assertEqual(res.status_code, 403)

        # 6. Admin console HTML page - Expect 403
        res = client.get("/admin", cookies=cookies)
        self.assertEqual(res.status_code, 403)

    def test_engineer_permissions(self):
        """Verify engineer role can triage alerts and inject spikes, but cannot access admin console."""
        create_user("test_engineer_01", password="TestPassword123!", role="engineer")
        token, _ = create_session("test_engineer_01", role="engineer")
        cookies = {"session_token": token}

        # 1. Can inject chaos spike -> 200
        res = client.post("/api/admin/simulate-spike", json={"server_name": "US-east-01", "metric": "cpu"}, cookies=cookies)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success"))

        # 2. Can triage alert -> 200
        res = client.post("/api/alerts/acknowledge", json={"server_name": "US-east-01", "action": "acknowledge", "note": "Checked thread pool"}, cookies=cookies)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success"))

        # 3. Cannot access admin user list -> 403
        res = client.get("/api/admin/users", cookies=cookies)
        self.assertEqual(res.status_code, 403)

        # 4. Cannot flush cache -> 403
        res = client.post("/api/admin/cache/flush", cookies=cookies)
        self.assertEqual(res.status_code, 403)

        # 5. Cannot access /admin HTML -> 403
        res = client.get("/admin", cookies=cookies)
        self.assertEqual(res.status_code, 403)

    def test_admin_permissions(self):
        """Verify admin (vamsi) has full unrestricted access across all admin and triage endpoints."""
        token, _ = create_session("vamsi", role="admin")
        cookies = {"session_token": token}

        # 1. Admin HTML Page -> 200
        res = client.get("/admin", cookies=cookies)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Admin Operations & Security Console", res.text)

        # 2. List Users API -> 200
        res = client.get("/api/admin/users", cookies=cookies)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(len(data.get("users", [])), 2)

        # 3. Update User Role -> 200
        create_user("promoted_user", password="Password123!", role="viewer")
        res = client.post("/api/admin/users/update-role", json={"username": "promoted_user", "role": "engineer"}, cookies=cookies)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success"))
        user_doc = find_user("promoted_user")
        self.assertEqual(user_doc.get("role"), "engineer")

        # 4. Flush Cache API -> 200
        res = client.post("/api/admin/cache/flush", cookies=cookies)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success"))

        # 5. Audit Logs API -> 200
        res = client.get("/api/admin/audit-logs", cookies=cookies)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json().get("success"))
        self.assertGreaterEqual(len(res.json().get("audit_logs", [])), 1)

    def test_signup_role_sanitization(self):
        """Verify public signup allows engineer and viewer, but sanitizes admin requests to viewer."""
        import time
        ts = int(time.time() * 1000)
        # 1. Register as engineer
        res = client.post("/signup", data={
            "username": f"dev_eng_{ts}",
            "email": f"dev_eng_{ts}@predictops.local",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
            "role": "engineer"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json().get("role"), "engineer")

        # 2. Attempt to register as admin (should sanitize to viewer)
        res = client.post("/signup", data={
            "username": f"hacker_{ts}",
            "email": f"hacker_{ts}@predictops.local",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
            "role": "admin"
        }, headers={"Accept": "application/json"})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json().get("role"), "viewer")


if __name__ == "__main__":
    unittest.main()
