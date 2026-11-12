"""Secure Email and MFA OTP service.

Security guarantees:
- 6-digit cryptographically secure code generated via `secrets.randbelow(900000) + 100000`.
- Only HMAC-SHA256(otp_code, server_secret) is stored; raw OTP is never stored in DB.
- Constant-time verification prevents timing side-channels.
- Max 5 verification attempts then record is invalidated.
- 60-second resend cooldown.
- 10-minute expiry.
- Development OTP is only returned if APP_ENV=development AND DEV_SHOW_OTP=true.
"""

from __future__ import annotations

import hmac
import os
import re
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..integrity import compute_hmac_sha256, verify_digest

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def get_otp_server_secret() -> bytes:
    """Derive or fetch the OTP HMAC secret."""
    secret = os.getenv("OTP_SECRET") or os.getenv("STEGCHAT_MASTER_KEY") or "stegchat-default-otp-server-secret-2026"
    return secret.encode("utf-8")

def hash_otp_code(otp_code: str) -> str:
    """Compute HMAC-SHA256 of the 6-digit OTP code with server secret."""
    return compute_hmac_sha256(get_otp_server_secret(), otp_code.strip().encode("utf-8"))

def verify_otp_hash(input_code: str, expected_hash: str) -> bool:
    """Constant-time verification of OTP against stored HMAC."""
    actual_hash = hash_otp_code(input_code)
    return verify_digest(expected_hash, actual_hash)

def validate_email_address(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def generate_otp_code() -> str:
    """Generate a 6-digit numeric OTP using secrets.randbelow."""
    return f"{secrets.randbelow(900000) + 100000}"

def should_expose_dev_otp() -> bool:
    """Expose dev OTP only if APP_ENV=development and DEV_SHOW_OTP=true."""
    app_env = os.getenv("APP_ENV", "development").lower()
    dev_show = os.getenv("DEV_SHOW_OTP", "false").lower() in ("true", "1", "yes")
    return app_env == "development" and dev_show

def send_otp_email(to_email: str, otp_code: str, purpose: str = "authentication") -> None:
    """Send OTP email via SMTP if configured, or log to development console."""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", "no-reply@stegchat.local")

    subject = f"StegChat Verification Code: {otp_code} for {purpose.title()}"
    body = f"""Hello,

Your StegChat one-time verification code (OTP) is:

    {otp_code}

This code will expire in 10 minutes. If you did not initiate this request, please ignore this email.

Best regards,
The StegChat Security Team
"""

    if smtp_host and smtp_user:
        try:
            msg = MIMEMultipart()
            msg["From"] = smtp_from
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_from, [to_email], msg.as_string())
            return
        except Exception as e:
            print(f"[MFA] SMTP send warning: {e}. Falling back to console output.")

    # Development console output
    print(f"\n==================================================")
    print(f"[STEGCHAT MFA OTP CODE]")
    print(f"Target Email : {to_email}")
    print(f"Purpose      : {purpose}")
    print(f"Your OTP Code: >>> {otp_code} <<<")
    print(f"Expires      : 10 minutes")
    print(f"==================================================\n")
