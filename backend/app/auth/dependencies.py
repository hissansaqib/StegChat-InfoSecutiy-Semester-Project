"""FastAPI authentication dependencies."""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import User, Session as DBSession
from datetime import datetime

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("stegchat_session")
    if not token:
        # Check Authorization header bearer token
        auth_hdr = request.headers.get("Authorization", "")
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    db_session = (
        db.query(DBSession)
        .filter(DBSession.token_hash == token, DBSession.revoked == False)
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

    return user

def get_optional_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None
