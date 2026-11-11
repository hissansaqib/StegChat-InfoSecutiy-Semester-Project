"""Configuration settings for StegChat backend.

Uses pydantic BaseSettings to read from environment variables.
Only the CORS allow list is needed for now.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseSettings, Field, validator

class Settings(BaseSettings):
    """Application settings loaded from environment or .env files.

    - ``CORS_ALLOW_ORIGINS``: comma‑separated list of origins allowed for CORS.
    - ``LAB_REQUIRE_AUTH``: toggle requiring auth for lab endpoints (default False).
    """

    cors_allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    lab_require_auth: bool = Field(default=False, description="Require auth for lab endpoints")

    @validator("cors_allow_origins", pre=True)
    def split_comma(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            # Split by comma and strip whitespace; ignore empty entries.
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_prefix = ""
        env_file = ".env"
        case_sensitive = False

