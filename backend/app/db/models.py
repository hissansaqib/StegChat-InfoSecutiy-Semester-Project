"""SQLAlchemy models for authentication and key storage.

These models are additive to the existing codebase.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey, Index, Integer, func
from sqlalchemy.orm import relationship

from .base import Base

def _generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_generate_uuid)
    username = Column(String(32), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, unique=True, index=True)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    mfa_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # JSON blob storing the encrypted vault bundle (optional)
    key_bundle = Column(String, nullable=True)

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_username_ci", func.lower(username), unique=True),
        Index("ix_users_email_ci", func.lower(email), unique=True),
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"

class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(String, primary_key=True, default=_generate_uuid)
    email = Column(String(255), nullable=False, index=True)
    otp_code = Column(String(8), nullable=False)
    purpose = Column(String(32), nullable=False)  # "register" or "login"
    user_id = Column(String, nullable=True)
    temp_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="sessions")
    audit_events = relationship("AuditEvent", back_populates="session", cascade="all, delete-orphan")

    def is_active(self) -> bool:
        return not self.revoked and self.expires_at > datetime.utcnow()

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True, default=_generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=True, index=True)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, server_default="CURRENT_TIMESTAMP", nullable=False)
    detail = Column(JSON, nullable=True)

    user = relationship("User", back_populates="audit_events")
    session = relationship("Session", back_populates="audit_events")
# Existing content continues...

# Conversation models
from sqlalchemy import Integer, Text, LargeBinary

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=_generate_uuid)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # members relationship defined below
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="conversation", cascade="all, delete-orphan")

class ConversationMember(Base):
    __tablename__ = "conversation_members"
    id = Column(String, primary_key=True, default=_generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    last_read_at = Column(DateTime, nullable=True)
    conversation = relationship("Conversation", backref="members")
    user = relationship("User", backref="conversation_members")
    __table_args__ = (Index("ix_conv_user_unique", "conversation_id", "user_id", unique=True),)

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=_generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    # encrypted payload stored as JSON string
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")

class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(String, primary_key=True, default=_generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    uploader_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    sha256 = Column(String(64), nullable=False)
    size = Column(Integer, nullable=False)
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    conversation = relationship("Conversation", back_populates="attachments")
    uploader = relationship("User")

# End of file
