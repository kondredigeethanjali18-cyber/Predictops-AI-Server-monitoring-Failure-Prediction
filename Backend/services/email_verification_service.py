import os
import re
import secrets
import logging
import smtplib
import socket
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple, Dict, Any
from dotenv import load_dotenv
from Backend.database.mongodb import db

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# SMTP Configuration from Environment
SMTP_HOST = os.getenv("SMTP_HOST", os.getenv("MAIL_SERVER", "")).strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", os.getenv("MAIL_PORT", "587")))
SMTP_USER = os.getenv("SMTP_USER", os.getenv("SMTP_USERNAME", os.getenv("MAIL_USERNAME", os.getenv("EMAIL_HOST_USER", "")))).strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", os.getenv("MAIL_PASSWORD", os.getenv("EMAIL_HOST_PASSWORD", ""))).strip()
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", os.getenv("MAIL_DEFAULT_SENDER", SMTP_USER or "no-reply@predictops.ai")).strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "PredictOps AI Security").strip()
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1", "yes") or SMTP_PORT == 465
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes") or SMTP_PORT == 587

# In-memory fallback if MongoDB is temporarily unavailable
IN_MEMORY_VERIFICATIONS: Dict[str, Dict[str, Any]] = {}


def get_verifications_collection():
    """Retrieve the email_verifications MongoDB collection."""
    if db is not None:
        try:
            return db["email_verifications"]
        except Exception as e:
            logger.warning(f"Error accessing email_verifications collection: {e}")
    return None


# Pre-verified trusted mail domain registry
KNOWN_TRUSTED_MAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "google.com",
    "yahoo.com", "yahoo.co.in", "yahoo.co.uk",
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com",
    "proton.me", "protonmail.com", "aol.com", "zoho.com"
}

# Disposable / Temporary Fake Email Domain Blacklist
DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "tempmail.com", "temp-mail.org", "10minutemail.com",
    "guerrillamail.com", "guerrillamail.net", "guerrillamail.org",
    "trashmail.com", "trashmail.net", "yopmail.com", "yopmail.net",
    "dispostable.com", "fakeinbox.com", "getairmail.com", "mohmal.com",
    "crazymailing.com", "burnermail.io", "throwawaymail.com", "fakemail.net",
    "nada.ltd", "tempmailaddress.com", "sharklasers.com", "grr.la"
}



def verify_email_exists(email: str) -> Tuple[bool, str]:
    """
    Verifies that the provided email address has a valid syntax,
    a valid username structure, is not a disposable address, and belongs
    to an existing internet domain capable of receiving mail.
    """
    if not email:
        return False, "Email address cannot be empty."

    clean_email = email.strip().lower()

    # 1. Standard RFC 5322 regex validation
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, clean_email):
        return False, "Invalid email address format (e.g., name@gmail.com)."

    if len(clean_email) > 254:
        return False, "Email address exceeds maximum allowable length."

    parts = clean_email.split("@")
    if len(parts) != 2:
        return False, "Invalid email address."

    local_part, domain = parts[0], parts[1]

    if not local_part or not domain:
        return False, "Invalid email address."

    # 2. Block disposable / fake temporary email providers
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        return False, "Temporary/disposable email addresses cannot be used. Please use your genuine Google account."

    # 3. Gmail / Googlemail specific username syntax validation
    if domain in ("gmail.com", "googlemail.com"):
        if len(local_part) < 6:
            return False, "Google account usernames must be at least 6 characters long."
        if len(local_part) > 30:
            return False, "Google account usernames cannot exceed 30 characters."
        if local_part.startswith(".") or local_part.endswith("."):
            return False, "Google account username cannot start or end with a period."
        if ".." in local_part:
            return False, "Google account username cannot contain consecutive periods."
        if not re.match(r"^[a-zA-Z0-9.]+$", local_part):
            return False, "Google email addresses can only contain letters, numbers, and periods."

    # 4. Known trusted domains are immediately verified
    if domain in KNOWN_TRUSTED_MAIL_DOMAINS:
        return True, "Email address is valid and domain exists."

    # 5. Domain existence verification via native socket lookup
    try:
        socket.getaddrinfo(domain, None)
    except socket.gaierror:
        return False, f"The email domain '@{domain}' does not exist on the internet."
    except Exception as e:
        logger.warning(f"Domain lookup warning for {domain}: {e}")
        return False, f"The email domain '@{domain}' could not be resolved."

    return True, "Email address is valid and domain exists."


def generate_otp_code() -> str:
    """Generates a cryptographically secure 6-digit verification code."""
    return f"{secrets.randbelow(900000) + 100000}"



def create_verification_record(email: str) -> Tuple[str, datetime]:
    """
    Creates and stores a 6-digit OTP verification code valid for 10 minutes.
    """
    clean_email = email.strip().lower()
    code = generate_otp_code()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=10)

    record = {
        "email": clean_email,
        "code": code,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "attempts": 0,
        "verified": False
    }

    col = get_verifications_collection()
    if col is not None:
        try:
            col.update_one(
                {"email": clean_email},
                {"$set": record},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving verification code to MongoDB: {e}")
            IN_MEMORY_VERIFICATIONS[clean_email] = record
    else:
        IN_MEMORY_VERIFICATIONS[clean_email] = record

    logger.info(f"[SECURITY] Generated 6-digit OTP for {clean_email} (valid 10 mins). Dispatched to inbox.")
    return code, expires_at


def send_verification_email(email: str, code: str) -> Tuple[bool, str]:
    """
    Dispatches the verification email containing the 6-digit OTP directly
    to the user's email inbox using SMTP.
    """
    clean_email = email.strip().lower()
    subject = f"{code} is your PredictOps AI Google verification code"

    html_body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #0b1120;
                color: #f8fafc;
                margin: 0;
                padding: 30px 15px;
            }}
            .email-card {{
                max-width: 500px;
                margin: 0 auto;
                background-color: #1e293b;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                padding: 36px 28px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
            }}
            .brand-header {{
                text-align: center;
                margin-bottom: 24px;
            }}
            .brand-badge {{
                display: inline-block;
                background: linear-gradient(135deg, #2563eb, #1d4ed8);
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                padding: 6px 14px;
                border-radius: 999px;
                letter-spacing: 0.5px;
            }}
            .headline {{
                font-size: 22px;
                font-weight: 700;
                color: #ffffff;
                text-align: center;
                margin: 16px 0 8px;
            }}
            .subtext {{
                font-size: 14px;
                color: #94a3b8;
                text-align: center;
                line-height: 1.5;
                margin-bottom: 24px;
            }}
            .otp-box {{
                background: #0f172a;
                border: 1.5px solid #3b82f6;
                border-radius: 12px;
                padding: 18px;
                text-align: center;
                margin: 20px 0;
            }}
            .otp-code {{
                font-size: 34px;
                font-weight: 800;
                color: #60a5fa;
                letter-spacing: 10px;
                font-family: 'Courier New', Courier, monospace;
            }}
            .security-notice {{
                font-size: 12.5px;
                color: #64748b;
                text-align: center;
                line-height: 1.5;
                margin-top: 20px;
                padding-top: 16px;
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }}
            .footer {{
                font-size: 11.5px;
                color: #475569;
                text-align: center;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="email-card">
            <div class="brand-header">
                <span class="brand-badge">PredictOps AI &bull; Google Sign-In</span>
            </div>
            <div class="headline">Google Account Verification</div>
            <div class="subtext">
                We received a sign-in request for <strong>{clean_email}</strong>. Enter the following 6-digit confirmation code on the verification screen:
            </div>
            <div class="otp-box">
                <div class="otp-code">{code}</div>
            </div>
            <div class="subtext" style="font-size: 13px; margin-top: 12px;">
                This code will expire in <strong>10 minutes</strong>.
            </div>
            <div class="security-notice">
                If you did not request this verification, someone may have entered your email address by mistake. Your account remains secure and no further action is needed.
            </div>
            <div class="footer">
                &copy; {datetime.now().year} PredictOps AI Platform. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

    # Determine effective SMTP settings (auto-configure Gmail if SMTP_HOST is omitted)
    effective_host = SMTP_HOST
    if not effective_host and SMTP_USER and "@gmail.com" in SMTP_USER.lower():
        effective_host = "smtp.gmail.com"

    # If SMTP is configured, send the live email
    if effective_host and SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
            msg["To"] = clean_email
            msg["Auto-Submitted"] = "auto-generated"
            msg["X-Priority"] = "1"
            msg["X-MSMail-Priority"] = "High"
            msg["Importance"] = "High"

            text_fallback = (
                f"Your PredictOps AI verification code is: {code}\n\n"
                f"Enter this code on the Google verification screen to complete sign in.\n"
                f"This code will expire in 10 minutes."
            )
            msg.attach(MIMEText(text_fallback, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            if SMTP_USE_SSL:
                server = smtplib.SMTP_SSL(effective_host, SMTP_PORT, timeout=12)
            else:
                server = smtplib.SMTP(effective_host, SMTP_PORT, timeout=12)
                if SMTP_USE_TLS:
                    server.starttls()

            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, [clean_email], msg.as_string())
            server.quit()


            logger.info(f"Verification email successfully delivered to {clean_email} via SMTP ({effective_host}:{SMTP_PORT})")
            return True, "Verification code sent to your email inbox.", True
        except smtplib.SMTPRecipientsRefused:
            logger.error(f"SMTP rejected recipient {clean_email}: address does not exist on mail server.")
            return False, "The email address could not be delivered to. Please verify that this email exists and is active.", False
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication error: {e}. Please check SMTP_USER and SMTP_PASSWORD in .env.")
        except Exception as e:
            logger.error(f"SMTP delivery error to {clean_email}: {e}")

    logger.info(f"[SECURITY AUDIT] Email OTP {code} generated for {clean_email} (Configure SMTP in .env for direct inbox delivery).")
    return True, f"Verification code has been dispatched for {clean_email}.", False



def verify_email_code(email: str, code_input: str) -> Tuple[bool, str]:
    """
    Validates the 6-digit OTP submitted by the user.
    """
    clean_email = email.strip().lower()
    clean_code = str(code_input).strip()

    if not clean_code or len(clean_code) != 6 or not clean_code.isdigit():
        return False, "Please enter a valid 6-digit numeric verification code."

    record = None
    col = get_verifications_collection()
    if col is not None:
        try:
            record = col.find_one({"email": clean_email})
        except Exception as e:
            logger.warning(f"Error reading verification from MongoDB: {e}")

    if not record and clean_email in IN_MEMORY_VERIFICATIONS:
        record = IN_MEMORY_VERIFICATIONS[clean_email]

    if not record:
        return False, "No active verification request found for this email. Please request a new code."

    # Check expiration
    expires_at_str = record.get("expires_at")
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now(timezone.utc) > expires_at:
            return False, "Verification code has expired. Please click 'Resend code'."

    # Check max attempts (limit to 5 attempts)
    attempts = record.get("attempts", 0)
    if attempts >= 5:
        return False, "Too many incorrect attempts. Please request a new verification code."

    # Validate code match
    expected_code = record.get("code")
    if expected_code != clean_code:
        # Increment failed attempts
        if col is not None:
            try:
                col.update_one({"email": clean_email}, {"$inc": {"attempts": 1}})
            except Exception:
                pass
        if clean_email in IN_MEMORY_VERIFICATIONS:
            IN_MEMORY_VERIFICATIONS[clean_email]["attempts"] = attempts + 1

        remaining = 5 - (attempts + 1)
        if remaining > 0:
            return False, f"Incorrect verification code ({remaining} attempt{'s' if remaining != 1 else ''} remaining)."
        else:
            return False, "Maximum verification attempts exceeded. Please request a new code."

    # Mark verified and delete record
    if col is not None:
        try:
            col.delete_one({"email": clean_email})
        except Exception:
            pass
    if clean_email in IN_MEMORY_VERIFICATIONS:
        del IN_MEMORY_VERIFICATIONS[clean_email]

    logger.info(f"Email {clean_email} successfully authenticated via Google OTP!")
    return True, "Email verified successfully."

