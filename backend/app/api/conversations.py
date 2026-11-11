"""Conversations and messaging router."""

import uuid
from datetime import datetime
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..db.models import Conversation, ConversationMember, Message, User
from ..auth.dependencies import get_current_user

router = APIRouter(tags=["conversations"])

class CreateConversationRequest(BaseModel):
    participant_id: Optional[str] = None
    title: Optional[str] = None

class MessageSendRequest(BaseModel):
    content: str
    carrier_id: Optional[str] = None
    carrier_bytes: Optional[str] = None  # Base64 stego medium
    is_stego: bool = False

@router.get("/conversations")
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = (
        db.query(ConversationMember)
        .filter(ConversationMember.user_id == current_user.id)
        .all()
    )
    results = []
    for m in memberships:
        conv = db.query(Conversation).filter(Conversation.id == m.conversation_id).first()
        if not conv:
            continue
        all_members = (
            db.query(ConversationMember)
            .filter(ConversationMember.conversation_id == conv.id)
            .all()
        )
        other_users = [
            db.query(User).filter(User.id == mem.user_id).first()
            for mem in all_members
            if mem.user_id != current_user.id
        ]
        other_name = other_users[0].display_name if other_users and other_users[0] else "Conversation"
        results.append({
            "id": conv.id,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "name": other_name,
        })
    return results

@router.post("/conversations")
def create_conversation(
    req: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv_id = str(uuid.uuid4())
    conv = Conversation(id=conv_id)
    db.add(conv)

    # Add current user
    db.add(ConversationMember(
        id=str(uuid.uuid4()),
        conversation_id=conv_id,
        user_id=current_user.id,
    ))

    # Add participant if specified
    if req.participant_id and req.participant_id != current_user.id:
        participant = db.query(User).filter(User.id == req.participant_id).first()
        if participant:
            db.add(ConversationMember(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                user_id=participant.id,
            ))

    db.commit()
    return {"id": conv_id}

@router.get("/conversations/{conversation_id}/messages")
def list_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify membership
    mem = (
        db.query(ConversationMember)
        .filter(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == current_user.id,
        )
        .first()
    )
    if not mem:
        raise HTTPException(status_code=403, detail="Not a member of this conversation")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    results = []
    for m in msgs:
        sender = db.query(User).filter(User.id == m.sender_id).first()
        results.append({
            "id": m.id,
            "sender_id": m.sender_id,
            "sender_name": sender.display_name if sender else "Unknown",
            "is_me": m.sender_id == current_user.id,
            "payload": m.payload,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })
    return results

@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    req: MessageSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    mem = (
        db.query(ConversationMember)
        .filter(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == current_user.id,
        )
        .first()
    )
    if not mem:
        raise HTTPException(status_code=403, detail="Not a member of this conversation")

    msg_id = str(uuid.uuid4())
    msg_payload = {
        "text": req.content,
        "is_stego": req.is_stego,
        "carrier_id": req.carrier_id,
        "carrier_bytes": req.carrier_bytes,
    }

    msg = Message(
        id=msg_id,
        conversation_id=conversation_id,
        sender_id=current_user.id,
        payload=msg_payload,
    )
    db.add(msg)
    db.commit()
    return {"id": msg_id, "status": "sent"}
