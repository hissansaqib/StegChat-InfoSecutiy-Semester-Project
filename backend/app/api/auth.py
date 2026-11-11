"""Auth router implementation with strict validation and Email MFA OTP."""

import re
import uuid
import bcrypt
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import User, Session as DBSession, OTPVerification
from ..auth.dependencies import get_current_user
from ..core.otp_service import validate_email_address, generate_otp_code, send_otp_email

router = APIRouter(tags=["auth"])

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long."
        )
    if not re.search(r"[A-Za-z]", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one letter."
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one number."
        )

# Request Schemas
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

class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None
    display_name: str
    is_admin: bool

# 1. INITIATE REGISTRATION (Validates constraints, stores pending info, sends OTP)
@router.post("/auth/register")
def initiate_registration(req: RegisterInitiateRequest, db: Session = Depends(get_db)):
    clean_username = req.username.strip().lower()
    clean_email = req.email.strip().lower()
    clean_display = req.display_name.strip()

    if not clean_username or len(clean_username) < 3 or len(clean_username) > 32:
        raise HTTPException(status_code=400, detail="Username must be between 3 and 32 characters.")

    if not re.match(r"^[a-zA-Z0-9_-]+$", clean_username):
        raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, underscores, and dashes.")

    if not validate_email_address(clean_email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address (e.g., name@domain.com).")

    if not clean_display or len(clean_display) < 2:
        raise HTTPException(status_code=400, detail="Display name must be at least 2 characters long.")

    validate_password_strength(req.password)

    # Constraint Check: Unique username
    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(status_code=400, detail="Username is already taken. Please choose another.")

    # Constraint Check: Unique email (Only one account per email)
    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(status_code=400, detail="An account is already registered with this email address.")

    # Generate 6-digit OTP
    otp_code = generate_otp_code()
    verification_id = str(uuid.uuid4())

    pending_data = {
        "username": clean_username,
        "email": clean_email,
        "display_name": clean_display,
        "password_hash": hash_password(req.password),
    }

    otp_record = OTPVerification(
        id=verification_id,
        email=clean_email,
        otp_code=otp_code,
        purpose="register",
        temp_data=pending_data,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        consumed=False,
    )
    db.add(otp_record)
    db.commit()

    # Dispatch email
    send_otp_email(clean_email, otp_code, purpose="Registration Verification")

    return {
        "status": "mfa_required",
        "message": f"Verification code sent to {clean_email}. Please enter the 6-digit code to complete registration.",
        "verification_id": verification_id,
        "email": clean_email,
        "dev_hint": f"Development OTP code: {otp_code}",
    }

# 2. INITIATE LOGIN (Checks credentials, sends OTP for MFA)
@router.post("/auth/login")
def initiate_login(req: LoginInitiateRequest, db: Session = Depends(get_db)):
    identifier = req.username_or_email.strip().lower()
    if not identifier:
        raise HTTPException(status_code=400, detail="Please enter your username or email address.")
    if not req.password:
        raise HTTPException(status_code=400, detail="Please enter your password.")

    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Account not found with provided username/email.")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password. Please verify and try again.")

    # Send MFA OTP
    otp_code = generate_otp_code()
    verification_id = str(uuid.uuid4())
    target_email = user.email or f"{user.username}@stegchat.local"

    otp_record = OTPVerification(
        id=verification_id,
        email=target_email,
        otp_code=otp_code,
        purpose="login",
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        consumed=False,
    )
    db.add(otp_record)
    db.commit()

    send_otp_email(target_email, otp_code, purpose="Login Authentication")

    return {
        "status": "mfa_required",
        "message": f"Security verification code dispatched to {target_email}.",
        "verification_id": verification_id,
        "email": target_email,
        "dev_hint": f"Development OTP code: {otp_code}",
    }

# 3. VERIFY OTP (Completes registration or login session)
@router.post("/auth/verify-otp")
def verify_otp(req: VerifyOTPRequest, response: Response, db: Session = Depends(get_db)):
    clean_code = req.otp_code.strip()
    record = db.query(OTPVerification).filter(
        OTPVerification.id == req.verification_id,
        OTPVerification.consumed == False,
    ).first()

    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired verification session. Please try again.")

    if record.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    if record.otp_code != clean_code:
        raise HTTPException(status_code=400, detail="Incorrect verification code. Please enter the valid 6-digit OTP.")

    # Mark consumed
    record.consumed = True

    if record.purpose == "register":
        data = record.temp_data
        # Double check email/username uniqueness before commit
        if db.query(User).filter(User.username == data["username"]).first():
            raise HTTPException(status_code=400, detail="Username was taken while verifying.")
        if db.query(User).filter(User.email == data["email"]).first():
            raise HTTPException(status_code=400, detail="Email was registered while verifying.")

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
    else:  # Login
        user = db.query(User).filter(User.id == record.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User account no longer exists.")

    # Create active session
    token = str(uuid.uuid4().hex)
    expires = datetime.utcnow() + timedelta(days=7)
    db_session = DBSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=token,
        expires_at=expires,
        revoked=False,
    )
    db.add(db_session)
    db.commit()
    db.refresh(user)

    response.set_cookie(
        key="stegchat_session",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=7 * 86400,
        path="/",
    )

    return {
        "status": "success",
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "is_admin": user.is_admin,
        },
    }

# 4. RESEND OTP
@router.post("/auth/resend-otp")
def resend_otp(req: ResendOTPRequest, db: Session = Depends(get_db)):
    record = db.query(OTPVerification).filter(OTPVerification.id == req.verification_id).first()
    if not record or record.consumed:
        raise HTTPException(status_code=400, detail="Cannot resend code for this session.")

    new_code = generate_otp_code()
    record.otp_code = new_code
    record.expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()

    send_otp_email(record.email, new_code, purpose="Resent Verification Code")
    return {
        "status": "resent",
        "message": f"A new verification code was sent to {record.email}.",
        "dev_hint": f"Development OTP code: {new_code}",
    }

@router.post("/auth/logout")
def logout(response: Response, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(DBSession).filter(DBSession.user_id == current_user.id).update({"revoked": True})
    db.commit()
    response.delete_cookie(key="stegchat_session", path="/")
    return {"status": "logged_out"}

@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        display_name=current_user.display_name,
        is_admin=current_user.is_admin,
    )
