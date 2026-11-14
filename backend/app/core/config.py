"""Configuration settings for StegChat backend.

Uses pydantic BaseSettings to read from environment variables.
"""

from __future__ import annotations

import pathlib
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine project repository root reliably regardless of current working directory
_CORE_DIR = pathlib.Path(__file__).resolve().parent
_REPO_ROOT = _CORE_DIR.parent.parent.parent
_DEFAULT_DATA_DIR = _REPO_ROOT / "data"
_DEFAULT_DATA_DIR.mkdir(exist_ok=True)
_DEFAULT_DB_FILE = _DEFAULT_DATA_DIR / "stegchat.db"
_DEFAULT_DB_URL = f"sqlite:///{_DEFAULT_DB_FILE.as_posix()}"

_DEFAULT_UPLOAD_DIR = _REPO_ROOT / "uploads"
_DEFAULT_UPLOAD_DIR.mkdir(exist_ok=True)

class Settings(BaseSettings):
    """Application settings loaded from environment or .env files."""

    database_url: str = Field(default=_DEFAULT_DB_URL, description="Database connection URL")
    stegchat_master_key: str = Field(default="", description="Master encryption key base64")
    text_carrier_deliverable: bool = Field(default=False, description="Make text-zw carrier deliverable")
    cors_allow_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    lab_require_auth: bool = Field(default=False, description="Require auth for lab endpoints")
    session_cookie_name: str = Field(default="stegchat_session", description="Name of the session cookie")
    session_expire_seconds: int = Field(default=86400, description="Session expiry in seconds")
    csrf_cookie_name: str = Field(default="stegchat_csrf", description="Name of the CSRF token cookie")
    app_env: str = Field(default="development", description="Application environment")
    dev_show_otp: bool = Field(default=False, description="Expose OTP in development")
    upload_dir: str = Field(default=str(_DEFAULT_UPLOAD_DIR), description="Directory for uploaded attachments")

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def split_comma(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=str(_REPO_ROOT / ".env"),
        case_sensitive=False,
        extra="allow",
    )

