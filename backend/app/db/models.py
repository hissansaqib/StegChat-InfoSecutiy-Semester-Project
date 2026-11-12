"""SQLAlchemy models for authentication, sessions, audit, and key storage."""

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
    otp_hash = Column(String(64), nullable=False)  # HMAC-SHA256(otp_code, server_secret)
    purpose = Column(String(32), nullable=False)  # "register" or "login"
    user_id = Column(String, nullable=True)
    temp_data = Column(JSON, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    consumed = Column(Boolean, default=False, nullable=False)

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=_generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA-256 of secrets.token_urlsafe(32)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
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
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    detail = Column(JSON, nullable=True)

    user = relationship("User", back_populates="audit_events")
    session = relationship("Session", back_populates="audit_events")

# ---------------------------------------------------------------------------
# Conversation & Experiment Models
# ---------------------------------------------------------------------------

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=_generate_uuid)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
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
    payload = Column(JSON, nullable=False)
    cover_sha256 = Column(String(64), nullable=True)
    stego_sha256 = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User")

class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    id = Column(String, primary_key=True, default=_generate_uuid)
    name = Column(String, nullable=False)
    carrier_id = Column(String, nullable=False)
    algorithm = Column(String, nullable=True, default="aes-256-gcm")
    payload_size = Column(Integer, nullable=False)
    cover_sha256 = Column(String(64), nullable=True)
    stego_sha256 = Column(String(64), nullable=True)
    recovery_rate = Column(Integer, default=1)
    embed_time_ms = Column(Integer, default=0)
    extract_time_ms = Column(Integer, default=0)
    status = Column(String, default="completed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

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
