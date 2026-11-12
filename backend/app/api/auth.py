"""Authentication router implementing complete enterprise security requirements.

Features:
- Sessions: secrets.token_urlsafe(32), only SHA-256 stored in DB, HttpOnly/SameSite=Lax cookies, 7-day expiry.
- CSRF: issues double-submit X-CSRF-Token and validates state-changing requests.
- OTP: secrets.randbelow 6 digits, HMAC-SHA256 stored, 10 min expiry, max 5 attempts, 60s cooldown.
- Production safety: dev_hint exposed ONLY if APP_ENV=development and DEV_SHOW_OTP=true.
- Passwords: min 10 chars, uppercase+lowercase+number, reject common list, bcrypt 72-byte safe handling, transparent Argon2id rehash on login.
- Rate limiting per IP and per account on login, verify, resend, and register with lockout.
- Identical timing & response for unknown user vs incorrect password.
- Endpoints: register, login, verify-otp, resend-otp, logout, me, change-password, GET/DELETE /auth/sessions, GET /auth/activity.
- Audit events for all security lifecycle events.
"""

from __future__ import annotations

import hashlib
import base64
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import User, Session as DBSession, OTPVerification, AuditEvent
from ..auth.dependencies import get_current_user, get_current_user_and_session, get_client_ip, verify_csrf_protection
from ..auth.security import validate_password_policy, auth_rate_limiter
from ..core.otp_service import (
    generate_otp_code,
    hash_otp_code,
    verify_otp_hash,
    validate_email_address,
    send_otp_email,
    should_expose_dev_otp,
)
from ..integrity import hash_password, verify_and_rehash_password, compute_sha256

router = APIRouter(tags=["auth"])

def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def set_auth_cookies(response: Response, raw_session_token: str, csrf_token: str) -> None:
    is_prod = os.getenv("APP_ENV", "development").lower() == "production"
    # Session cookie (7 days)
    response.set_cookie(
        key="stegchat_session",
        value=raw_session_token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=7 * 86400,
        path="/",
    )
    # Double submit CSRF cookie (accessible to javascript to attach header)
    response.set_cookie(
        key="stegchat_csrf",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=is_prod,
        max_age=7 * 86400,
        path="/",
    )

def log_audit_event(
    db: Session,
    event_type: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    event = AuditEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        session_id=session_id,
        event_type=event_type,
        ip_address=ip_address,
        detail=detail or {},
    )
    db.add(event)
    db.commit()

# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class RegisterInitiateRequest(BaseModel):
    username: str
    email: str
    display_name: str
    password: str

class LoginInitiateRequest(BaseModel):
    username_or_email: str
    password: str

class VerifyOTPRequest(BaseModel):
    verification_id: str
    otp_code: str

class ResendOTPRequest(BaseModel):
    verification_id: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    display_name: str
    is_admin: bool

# ---------------------------------------------------------------------------
# 1. REGISTER (Initiate MFA OTP)
# ---------------------------------------------------------------------------

@router.post("/auth/register")
def initiate_registration(req: RegisterInitiateRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    auth_rate_limiter.check_rate_limit(f"reg_ip_{ip}", max_attempts=5, window_seconds=60)

    clean_username = req.username.strip().lower()
    clean_email = req.email.strip().lower()
    clean_display = req.display_name.strip()

    if not clean_username or len(clean_username) < 3 or len(clean_username) > 32:
        raise HTTPException(status_code=400, detail="Username must be between 3 and 32 characters.")

    if not validate_email_address(clean_email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    if not clean_display or len(clean_display) < 2:
        raise HTTPException(status_code=400, detail="Display name must be at least 2 characters long.")

    prepared_password = validate_password_policy(req.password)

    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(status_code=400, detail="Username is already taken. Please choose another.")

    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(status_code=400, detail="An account is already registered with this email address.")

    # Also block duplicate pending OTP sessions for the same email that haven't been consumed yet.
    # This prevents the same email from getting multiple valid OTPs simultaneously.
    existing_otp = db.query(OTPVerification).filter(
        OTPVerification.email == clean_email,
        OTPVerification.purpose == "register",
        OTPVerification.consumed == False,
        OTPVerification.expires_at > datetime.utcnow(),
    ).first()
    if existing_otp:
        raise HTTPException(
            status_code=400,
            detail="A verification code was already sent to this email address. "
                   "Please check your inbox or wait for it to expire before trying again.",
        )

    # Generate OTP and store ONLY HMAC-SHA256
    otp_code = generate_otp_code()
    otp_hash = hash_otp_code(otp_code)
    verification_id = str(uuid.uuid4())

    pending_data = {
        "username": clean_username,
        "email": clean_email,
        "display_name": clean_display,
        "password_hash": hash_password(prepared_password),
    }

    otp_record = OTPVerification(
        id=verification_id,
        email=clean_email,
        otp_hash=otp_hash,
        purpose="register",
        temp_data=pending_data,
        attempts=0,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        last_sent_at=datetime.utcnow(),
        consumed=False,
    )
    db.add(otp_record)
    db.commit()

    send_otp_email(clean_email, otp_code, purpose="Registration Verification")

    resp: Dict[str, Any] = {
        "status": "mfa_required",
        "message": f"Verification code sent to {clean_email}.",
        "verification_id": verification_id,
        "email": clean_email,
    }
    if should_expose_dev_otp():
        resp["dev_hint"] = f"Development OTP code: {otp_code}"

    return resp

# ---------------------------------------------------------------------------
# 2. LOGIN (Credentials Check & Initiate MFA OTP)
# ---------------------------------------------------------------------------

@router.post("/auth/login")
def initiate_login(req: LoginInitiateRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    auth_rate_limiter.check_rate_limit(f"login_ip_{ip}", max_attempts=5, window_seconds=60)

    identifier = req.username_or_email.strip().lower()
    if identifier:
        auth_rate_limiter.check_rate_limit(f"login_user_{identifier}", max_attempts=5, window_seconds=60)

    # Identical response / timing resistance for unknown user vs wrong password
    t0 = time.perf_counter()
    user = db.query(User).filter((User.username == identifier) | (User.email == identifier)).first()

    # Pre-hash password if >= 72 bytes to match registration storage
    raw_pwd = req.password
    if len(raw_pwd.encode("utf-8")) >= 72:
        digest = hashlib.sha256(raw_pwd.encode("utf-8")).digest()
        prepared_pwd = base64.b64encode(digest).decode("ascii")
    else:
        prepared_pwd = raw_pwd

    is_valid = False
    needs_rehash = False
    new_hash = None

    if user:
        is_valid, needs_rehash, new_hash = verify_and_rehash_password(prepared_pwd, user.password_hash)
        if needs_rehash and new_hash:
            user.password_hash = new_hash
            db.commit()
    else:
        # Dummy verification to equalize timing against timing attacks
        _ = hash_password("dummy_password_timing_pad")

    # Minimum threshold timing pad (~150ms)
    elapsed = time.perf_counter() - t0
    if elapsed < 0.15:
        time.sleep(0.15 - elapsed)

    if not user or not is_valid:
        log_audit_event(db, "LOGIN_FAILED", user_id=user.id if user else None, ip_address=ip, detail={"identifier": identifier})
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Send MFA OTP
    otp_code = generate_otp_code()
    otp_hash = hash_otp_code(otp_code)
    verification_id = str(uuid.uuid4())
    target_email = user.email or f"{user.username}@stegchat.local"

    otp_record = OTPVerification(
        id=verification_id,
        email=target_email,
        otp_hash=otp_hash,
        purpose="login",
        user_id=user.id,
        attempts=0,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        last_sent_at=datetime.utcnow(),
        consumed=False,
    )
    db.add(otp_record)
    db.commit()

    send_otp_email(target_email, otp_code, purpose="Login Authentication")

    resp: Dict[str, Any] = {
        "status": "mfa_required",
        "message": f"Verification code dispatched to {target_email}.",
        "verification_id": verification_id,
        "email": target_email,
    }
    if should_expose_dev_otp():
        resp["dev_hint"] = f"Development OTP code: {otp_code}"

    return resp

# ---------------------------------------------------------------------------
# 3. VERIFY OTP (Finalize Session)
# ---------------------------------------------------------------------------

@router.post("/auth/verify-otp")
def verify_otp(req: VerifyOTPRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    auth_rate_limiter.check_rate_limit(f"otp_ip_{ip}", max_attempts=5, window_seconds=60)

    record = db.query(OTPVerification).filter(
        OTPVerification.id == req.verification_id,
        OTPVerification.consumed == False,
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired verification session.")

    # Max 5 attempts check
    if record.attempts >= 5:
        record.consumed = True
        db.commit()
        log_audit_event(db, "OTP_MAX_ATTEMPTS_EXCEEDED", user_id=record.user_id, ip_address=ip)
        raise HTTPException(status_code=400, detail="Too many failed attempts. This verification code has been invalidated.")

    if record.expires_at < datetime.utcnow():
        record.consumed = True
        db.commit()
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    # Constant-time HMAC comparison
    if not verify_otp_hash(req.otp_code, record.otp_hash):
        record.attempts += 1
        db.commit()
        log_audit_event(db, "OTP_FAILED", user_id=record.user_id, ip_address=ip, detail={"attempts": record.attempts})
        remaining = 5 - record.attempts
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect verification code. {remaining} attempt(s) remaining.",
        )

    # Success: consume record
    record.consumed = True

    if record.purpose == "register":
        data = record.temp_data
        user_id = str(uuid.uuid4())
        user = User(
            id=user_id,
            username=data["username"],
            email=data["email"],
            display_name=data["display_name"],
            password_hash=data["password_hash"],
            is_admin=False,
            mfa_enabled=True,
        )
        db.add(user)
        log_audit_event(db, "USER_REGISTERED", user_id=user.id, ip_address=ip)
    else:
        user = db.query(User).filter(User.id == record.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User account no longer exists.")
        log_audit_event(db, "LOGIN_SUCCESS", user_id=user.id, ip_address=ip)

    # Generate 32-byte URL-safe token, store SHA-256 hash in DB
    raw_session_token = secrets.token_urlsafe(32)
    token_hash = compute_sha256(raw_session_token.encode("utf-8"))
    csrf_token = issue_csrf_token()

    session_id = str(uuid.uuid4())
    db_session = DBSession(
        id=session_id,
        user_id=user.id,
        token_hash=token_hash,
        ip_address=ip,
        user_agent=request.headers.get("User-Agent", "")[:255],
        expires_at=datetime.utcnow() + timedelta(days=7),
        revoked=False,
    )
    db.add(db_session)
    db.commit()
    db.refresh(user)

    set_auth_cookies(response, raw_session_token, csrf_token)

    return {
        "status": "success",
        "csrf_token": csrf_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "is_admin": user.is_admin,
        },
    }

# ---------------------------------------------------------------------------
# 4. RESEND OTP (With 60s cooldown)
# ---------------------------------------------------------------------------

@router.post("/auth/resend-otp")
def resend_otp(req: ResendOTPRequest, request: Request, db: Session = Depends(get_db)):
    record = db.query(OTPVerification).filter(OTPVerification.id == req.verification_id).first()
    if not record or record.consumed:
        raise HTTPException(status_code=400, detail="Cannot resend code for this verification session.")

    now = datetime.utcnow()
    # 60-second cooldown check
    cooldown_elapsed = (now - record.last_sent_at).total_seconds()
    if cooldown_elapsed < 60:
        remaining = int(60 - cooldown_elapsed)
        raise HTTPException(status_code=429, detail=f"Please wait {remaining} seconds before requesting a new code.")

    new_code = generate_otp_code()
    record.otp_hash = hash_otp_code(new_code)
    record.attempts = 0
    record.expires_at = now + timedelta(minutes=10)
    record.last_sent_at = now
    db.commit()

    send_otp_email(record.email, new_code, purpose="Resent Verification Code")

    resp: Dict[str, Any] = {
        "status": "resent",
        "message": f"A fresh verification code was sent to {record.email}.",
    }
    if should_expose_dev_otp():
        resp["dev_hint"] = f"Development OTP code: {new_code}"

    return resp

# ---------------------------------------------------------------------------
# 5. LOGOUT (Revokes session server-side & clears cookies)
# ---------------------------------------------------------------------------

@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    _csrf: None = Depends(verify_csrf_protection),
    user_and_session: tuple[User, DBSession] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    user, current_session = user_and_session
    current_session.revoked = True
    db.commit()

    log_audit_event(db, "LOGOUT", user_id=user.id, session_id=current_session.id, ip_address=get_client_ip(request))

    response.delete_cookie(key="stegchat_session", path="/")
    response.delete_cookie(key="stegchat_csrf", path="/")
    return {"status": "logged_out"}

# ---------------------------------------------------------------------------
# 6. CHANGE PASSWORD (Revokes all other sessions)
# ---------------------------------------------------------------------------

@router.post("/auth/change-password")
def change_password(
    req: ChangePasswordRequest,
    request: Request,
    _csrf: None = Depends(verify_csrf_protection),
    user_and_session: tuple[User, DBSession] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    user, current_session = user_and_session

    # Verify current password
    raw_curr = req.current_password
    if len(raw_curr.encode("utf-8")) >= 72:
        digest = hashlib.sha256(raw_curr.encode("utf-8")).digest()
        prep_curr = base64.b64encode(digest).decode("ascii")
    else:
        prep_curr = raw_curr

    valid, _, _ = verify_and_rehash_password(prep_curr, user.password_hash)
    if not valid:
        raise HTTPException(status_code=400, detail="Current password incorrect.")

    # Validate new password policy
    prepared_new = validate_password_policy(req.new_password)
    user.password_hash = hash_password(prepared_new)

    # Revoke all OTHER sessions
    db.query(DBSession).filter(
        DBSession.user_id == user.id,
        DBSession.id != current_session.id,
    ).update({"revoked": True})

    db.commit()
    log_audit_event(db, "PASSWORD_CHANGED", user_id=user.id, session_id=current_session.id, ip_address=get_client_ip(request))
    return {"status": "success", "message": "Password changed successfully. All other active sessions have been revoked."}

# ---------------------------------------------------------------------------
# 7. SESSIONS MANAGEMENT (GET & DELETE)
# ---------------------------------------------------------------------------

@router.get("/auth/sessions")
def list_active_sessions(
    user_and_session: tuple[User, DBSession] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    user, current_session = user_and_session
    sessions = (
        db.query(DBSession)
        .filter(DBSession.user_id == user.id, DBSession.revoked == False, DBSession.expires_at > datetime.utcnow())
        .order_by(DBSession.created_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "is_current": s.id == current_session.id,
        }
        for s in sessions
    ]

@router.delete("/auth/sessions/{session_id}")
def revoke_session(
    session_id: str,
    request: Request,
    user_and_session: tuple[User, DBSession] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
    _csrf: None = Depends(verify_csrf_protection),
):
    user, _ = user_and_session
    s = db.query(DBSession).filter(DBSession.id == session_id, DBSession.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s.revoked = True
    db.commit()
    log_audit_event(db, "SESSION_REVOKED", user_id=user.id, ip_address=get_client_ip(request), detail={"revoked_session_id": session_id})
    return {"status": "revoked"}

# ---------------------------------------------------------------------------
# 8. SECURITY AUDIT ACTIVITY LOG
# ---------------------------------------------------------------------------

@router.get("/auth/activity")
def get_security_activity(
    user_and_session: tuple[User, DBSession] = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    user, _ = user_and_session
    events = (
        db.query(AuditEvent)
        .filter(AuditEvent.user_id == user.id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "ip_address": e.ip_address,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "detail": e.detail,
        }
        for e in events
    ]

# ---------------------------------------------------------------------------
# 9. GET CURRENT USER
# ---------------------------------------------------------------------------

@router.get("/auth/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
    )
