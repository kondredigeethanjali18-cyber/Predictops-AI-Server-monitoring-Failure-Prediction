import pytest
import sys
import os
import re
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, r"C:\MainGP_pridictOps")

from Backend.routes.auth import validate_username, validate_password, validate_email, RESERVED_USERNAMES
from fastapi.testclient import TestClient
from Backend.main import app

client = TestClient(app)

def test_username_validation_rules():
    # 1. Pure numbers must be strictly rejected
    pure_numbers = ["123", "987654", "00000", "1234567890", "12345"]
    for num in pure_numbers:
        valid, msg = validate_username(num)
        assert not valid, f"Expected {num} to be invalid, but got valid=True"
        assert "numbers only" in msg.lower()

    # 2. Pure letters must be accepted
    pure_letters = ["vamsi", "geethanjali", "john", "alice", "developer"]
    for letters in pure_letters:
        valid, msg = validate_username(letters)
        assert valid, f"Expected {letters} to be valid, but got: {msg}"

    # 3. Mixed characters must be accepted
    mixed_usernames = ["vamsi123", "dev_01", "ops-team.9", "server99", "user_abc_1"]
    for uname in mixed_usernames:
        valid, msg = validate_username(uname)
        assert valid, f"Expected {uname} to be valid, but got: {msg}"

    # 4. Too short (<3) and too long (>30)
    assert not validate_username("ab")[0]
    assert not validate_username("a" * 31)[0]

    # 5. Invalid characters
    assert not validate_username("user@name")[0]
    assert not validate_username("user#1")[0]
    assert not validate_username("user$1")[0]

    # 6. Starts or ends with special characters
    assert not validate_username("_user123")[0]
    assert not validate_username("user123_")[0]
    assert not validate_username(".user123")[0]
    assert not validate_username("-user123")[0]

    # 7. Consecutive special characters
    assert not validate_username("user..name")[0]
    assert not validate_username("user__name")[0]
    assert not validate_username("user--name")[0]

    # 8. Reserved usernames
    for reserved in ["admin", "root", "system", "predictops", "security"]:
        valid, msg = validate_username(reserved)
        assert not valid
        assert "reserved" in msg.lower()


def test_email_validation_rules():
    # Valid emails
    valid_emails = [
        "vamsi@gmail.com",
        "geethanjali@yahoo.com",
        "ops.admin@outlook.com",
        "sre-team@proton.me",
        "dev_user1@icloud.com"
    ]
    for email in valid_emails:
        valid, msg = validate_email(email)
        assert valid, f"Expected '{email}' to be valid, but got: {msg}"

    # Missing / empty
    assert not validate_email("")[0]
    assert not validate_email("   ")[0]

    # Spaces in email
    assert not validate_email("user @gmail.com")[0]
    assert not validate_email("user@ gmail.com")[0]

    # Invalid formats
    assert not validate_email("plainaddress")[0]
    assert not validate_email("@missingusername.com")[0]
    assert not validate_email("username@.com")[0]
    assert not validate_email("username@com")[0]

    # Consecutive or starting/ending dots in username
    assert not validate_email(".username@gmail.com")[0]
    assert not validate_email("username.@gmail.com")[0]
    assert not validate_email("user..name@gmail.com")[0]

    # Length > 100
    assert not validate_email("a" * 90 + "@domain.com")[0]

    # Disposable temporary emails
    disposables = ["test@mailinator.com", "fake@tempmail.com", "temp@10minutemail.com", "user@sharklasers.com"]
    for disp in disposables:
        valid, msg = validate_email(disp)
        assert not valid, f"Expected disposable '{disp}' to be rejected"
        assert "disposable" in msg.lower() or "temporary" in msg.lower()


def test_password_validation_rules():
    # Strong valid password
    valid, msg = validate_password("StrongPass123!", username="testdev")
    assert valid, f"Expected valid password, got: {msg}"

    # Password containing username
    valid, msg = validate_password("testdevPass123!", username="testdev")
    assert not valid
    assert "cannot contain your username" in msg.lower()

    # Missing uppercase
    assert not validate_password("lowercase123!", username="testdev")[0]
    # Missing lowercase
    assert not validate_password("UPPERCASE123!", username="testdev")[0]
    # Missing number
    assert not validate_password("NoNumbersHere!", username="testdev")[0]
    # Missing special char
    assert not validate_password("NoSpecialChar123", username="testdev")[0]
    # Too short
    assert not validate_password("Sh1!", username="testdev")[0]


def test_record_generation_time_10s():
    # 1. Check collector script
    col_path = Path(r"C:\MainGP_pridictOps\collector\metrics_collector.py")
    col_content = col_path.read_text(encoding="utf-8")
    assert "time.sleep(10)" in col_content, "collector must sleep for 10 seconds"
    assert "10-second" in col_content, "collector must log 10-second interval"

    # 2. Check main.py auto-telemetry generator
    main_path = Path(r"C:\MainGP_pridictOps\Backend\main.py")
    main_content = main_path.read_text(encoding="utf-8")
    assert "await asyncio.sleep(10)" in main_content, "main.py auto-telemetry must sleep for 10 seconds"

    # 3. Check landing.js, dashboard.js, analytics.js
    landing_js = Path(r"C:\MainGP_pridictOps\Backend\static\js\landing.js").read_text(encoding="utf-8")
    assert "REFRESH_INTERVAL_SECONDS = 10" in landing_js

    dash_js = Path(r"C:\MainGP_pridictOps\Backend\static\js\dashboard.js").read_text(encoding="utf-8")
    assert "DASH_REFRESH_INTERVAL = 10" in dash_js

    analytics_js = Path(r"C:\MainGP_pridictOps\Backend\static\js\analytics.js").read_text(encoding="utf-8")
    assert "ANALYTICS_REFRESH_INTERVAL = 10" in analytics_js


def test_login_page_checklists():
    login_html_path = Path(r"C:\MainGP_pridictOps\Backend\templates\login.html")
    content = login_html_path.read_text(encoding="utf-8")
    
    # Username checklist
    assert "usernameChecklist" in content
    assert "chkUserLen" in content
    assert "validateSignupUsername" in content
    
    # Email checklist
    assert "emailChecklist" in content
    assert "chkEmailFormat" in content
    assert "chkEmailDomain" in content
    assert "chkEmailLength" in content
    assert "chkEmailGenuine" in content
    assert "validateSignupEmail" in content


def test_signup_api_rejections_and_success():
    # 1. Reject pure numbers username via JSON API
    res = client.post(
        "/signup",
        json={"username": "123456", "email": "test@gmail.com", "password": "Password123!"},
        headers={"Accept": "application/json"}
    )
    assert res.status_code == 400
    assert "numbers only" in res.json().get("detail", "").lower()

    # 2. Reject disposable / invalid email
    res_email = client.post(
        "/signup",
        json={"username": "devuser99", "email": "test@mailinator.com", "password": "Password123!"},
        headers={"Accept": "application/json"}
    )
    assert res_email.status_code == 400
    assert "disposable" in res_email.json().get("detail", "").lower() or "temporary" in res_email.json().get("detail", "").lower()

    # 3. Reject reserved username
    res_resv = client.post(
        "/signup",
        json={"username": "admin", "email": "admin@gmail.com", "password": "Password123!"},
        headers={"Accept": "application/json"}
    )
    assert res_resv.status_code == 400
    assert "reserved" in res_resv.json().get("detail", "").lower()

    # 4. Reject password containing username
    res_pwd = client.post(
        "/signup",
        json={"username": "validuser1", "email": "user1@gmail.com", "password": "validuser1Pass!"},
        headers={"Accept": "application/json"}
    )
    assert res_pwd.status_code == 400
    assert "cannot contain your username" in res_pwd.json().get("detail", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
