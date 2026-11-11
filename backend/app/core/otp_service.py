"""Email and MFA OTP service."""

import os
import random
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_email_address(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))

def generate_otp_code() -> str:
    """Generate a 6-digit numeric OTP."""
    return f"{random.randint(100000, 999999)}"

def send_otp_email(to_email: str, otp_code: str, purpose: str = "authentication") -> None:
    """Send OTP email via SMTP if configured, or log clearly to console in development mode."""
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
            print(f"[MFA] Sent OTP email to {to_email}")
            return
        except Exception as e:
            print(f"[MFA] Warning: Failed to send email via SMTP ({e}). Fallback to console output.")

    # Development fallback: Output prominently to console & log
    print(f"\n==================================================")
    print(f"[STEGCHAT MFA OTP CODE]")
    print(f"Target Email : {to_email}")
    print(f"Purpose      : {purpose}")
    print(f"Your OTP Code: >>> {otp_code} <<<")
    print(f"Expires      : 10 minutes")
    print(f"==================================================\n")

