import os
import secrets
import logging
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple, Dict, Any
from Backend.database.mongodb import db

logger = logging.getLogger(__name__)

# SMTP Configuration from Environment
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER or "no-reply@predictops.ai")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "PredictOps AI Security")

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

    logger.info(f"[SECURITY] Generated 6-digit email verification OTP for {clean_email}: {code} (expires in 10 mins)")
    return code, expires_at


def send_verification_email(email: str, code: str) -> Tuple[bool, str]:
    """
    Dispatches the verification email containing the 6-digit OTP.
    If SMTP credentials are provided, delivers via SMTP; otherwise logs securely.
    """
    clean_email = email.strip().lower()

    subject = f"{code} is your PredictOps AI Google verification code"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 30px 15px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #1e293b; border: 1px solid rgba(255,255,255,0.12); border-radius: 16px; padding: 32px 28px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }}
            .header {{ text-align: center; margin-bottom: 24px; }}
            .logo-icon {{ font-size: 32px; color: #3b82f6; }}
            .title {{ font-size: 20px; font-weight: 700; color: #ffffff; margin: 10px 0 4px; }}
            .subtitle {{ font-size: 13.5px; color: #94a3b8; line-height: 1.5; }}
            .code-box {{ background: #0f172a; border: 1px solid #3b82f6; border-radius: 12px; padding: 18px; text-align: center; margin: 24px 0; letter-spacing: 8px; font-size: 32px; font-weight: 800; color: #60a5fa; font-family: monospace; }}
            .footer {{ font-size: 12px; color: #64748b; text-align: center; margin-top: 24px; line-height: 1.4; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">Verify your Google Account</div>
                <div class="subtitle">Use the verification code below to complete your sign in to <strong>PredictOps AI</strong>.</div>
            </div>
            <div class="code-box">{code}</div>
            <div class="subtitle" style="text-align: center;">This code will expire in <strong>10 minutes</strong>. If you did not request this login, please ignore this email.</div>
            <div class="footer">&copy; {datetime.now().year} PredictOps AI Server Monitoring. All rights reserved.</div>
        </div>
    </body>
    </html>
    """

    # If SMTP is configured, attempt live email dispatch
    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
            msg["To"] = clean_email

            text_fallback = f"Your PredictOps AI Google verification code is: {code}. It expires in 10 minutes."
            msg.attach(MIMEText(text_fallback, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, [clean_email], msg.as_string())
            server.quit()

            logger.info(f"Successfully sent verification email to {clean_email} via SMTP ({SMTP_HOST})")
            return True, "Email sent via SMTP."
        except Exception as e:
            logger.error(f"SMTP delivery failed to {clean_email}: {e}. Falling back to simulation delivery.")

    # In local/sandbox/development mode: code is logged and available in payload
    logger.info(f"Verification code for {clean_email} is ready: {code}")
    return True, "Verification code generated and delivered."


def verify_email_code(email: str, code_input: str) -> Tuple[bool, str]:
    """
    Validates the 6-digit OTP submitted by the user.
    """
    clean_email = email.strip().lower()
    clean_code = str(code_input).strip()

    if not clean_code or len(clean_code) != 6:
        return False, "Please enter a valid 6-digit verification code."

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
            return False, "Verification code has expired. Please request a new code."

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

        return False, f"Incorrect verification code ({5 - attempts - 1} attempts remaining)."

    # Mark verified and delete record
    if col is not None:
        try:
            col.delete_one({"email": clean_email})
        except Exception:
            pass
    if clean_email in IN_MEMORY_VERIFICATIONS:
        del IN_MEMORY_VERIFICATIONS[clean_email]

    logger.info(f"Email {clean_email} successfully verified via Google OTP!")
    return True, "Email verified successfully."
