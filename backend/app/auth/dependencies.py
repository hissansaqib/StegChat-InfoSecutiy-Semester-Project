"""FastAPI authentication and CSRF dependencies.

- Session verification: reads raw cookie `stegchat_session`, hashes with SHA-256, looks up in DB.
- CSRF protection: double-submit cookie `stegchat_csrf` + header `X-CSRF-Token`, plus Origin header check on state-changing requests (POST, PUT, PATCH, DELETE).
"""

from __future__ import annotations

import os
from datetime import datetime
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import User, Session as DBSession
from ..integrity import compute_sha256, verify_digest

def get_client_ip(request: Request) -> str:
    """Extract client IP address handling reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

def verify_csrf_protection(request: Request) -> None:
    """Enforce CSRF protection on state-changing HTTP requests.
    
    1. Origin / Referer validation if provided.
    2. Double-submit cookie verification: `stegchat_csrf` cookie must match `X-CSRF-Token` header.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Check origin/referer
    origin = request.headers.get("Origin") or request.headers.get("Referer")
    app_env = os.getenv("APP_ENV", "development").lower()

    if origin and app_env == "production":
        # Ensure origin matches host
        host = request.headers.get("Host", "")
        if host and host not in origin:
            raise HTTPException(status_code=403, detail="CSRF check failed: Origin header mismatch.")

    # Double submit check
    csrf_cookie = request.cookies.get("stegchat_csrf")
    csrf_header = request.headers.get("X-CSRF-Token")

    # If CSRF cookie was issued, require matching header
    if csrf_cookie:
        if not csrf_header or not verify_digest(csrf_cookie, csrf_header):
            raise HTTPException(status_code=403, detail="CSRF verification failed: Token mismatch or missing X-CSRF-Token header.")

def get_current_user_and_session(
    request: Request,
    db: Session = Depends(get_db),
) -> tuple[User, DBSession]:
    """Retrieve authenticated user and session using SHA-256 token hashing."""
    raw_token = request.cookies.get("stegchat_session")
    if not raw_token:
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            raw_token = auth_hdr[7:].strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Hash raw token with SHA-256 to query database
    token_hash = compute_sha256(raw_token.encode("utf-8"))

    db_session = (
        db.query(DBSession)
        .filter(DBSession.token_hash == token_hash, DBSession.revoked == False)
        .first()
    )

    if not db_session or db_session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = db.query(User).filter(User.id == db_session.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user, db_session

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    user, _ = get_current_user_and_session(request, db)
    return user

def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    try:
        user, _ = get_current_user_and_session(request, db)
        return user
    except HTTPException:
        return None
