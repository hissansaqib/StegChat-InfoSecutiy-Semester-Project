"""Users API router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import User
from ..auth.dependencies import get_current_user

router = APIRouter(tags=["users"])

class UpdateUserRequest(BaseModel):
    display_name: str | None = None

class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str
    is_admin: bool

@router.get("/users/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        is_admin=current_user.is_admin,
    )

@router.patch("/users/me", response_model=UserResponse)
def update_me(
    req: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if req.display_name:
        current_user.display_name = req.display_name
        db.commit()
        db.refresh(current_user)
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        is_admin=current_user.is_admin,
    )

@router.get("/users", response_model=list[UserResponse])
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            is_admin=u.is_admin,
        )
        for u in users
    ]
