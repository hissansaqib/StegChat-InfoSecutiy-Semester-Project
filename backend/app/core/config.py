"""Configuration settings for StegChat backend.

Uses pydantic BaseSettings to read from environment variables.
"""

from __future__ import annotations

from typing import List
from pydantic import Field, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment or .env files."""

    database_url: str = Field(default="sqlite:///./stegchat.db", description="Database connection URL")
    stegchat_master_key: str = Field(default="", description="Master encryption key base64")
    text_carrier_deliverable: bool = Field(default=False, description="Make text-zw carrier deliverable")
    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    lab_require_auth: bool = Field(default=False, description="Require auth for lab endpoints")
    session_cookie_name: str = Field(default="stegchat_session", description="Name of the session cookie")
    session_expire_seconds: int = Field(default=86400, description="Session expiry in seconds")
    csrf_cookie_name: str = Field(default="stegchat_csrf", description="Name of the CSRF token cookie")
    app_env: str = Field(default="development", description="Application environment")
    dev_show_otp: bool = Field(default=False, description="Expose OTP in development", env="DEV_SHOW_OTP")

    @validator("cors_allow_origins", pre=True)
    def split_comma(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_prefix = ""
        env_file = ".env"
        case_sensitive = False
        extra = "allow"
