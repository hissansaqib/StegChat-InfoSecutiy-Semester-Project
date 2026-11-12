"""Rate limiter, password policy, and common password blacklist."""

from __future__ import annotations

import base64
import hashlib
import os
import re
import time
from typing import Dict, Tuple
from fastapi import HTTPException

# Common passwords list for blacklist rejection
COMMON_PASSWORDS = {
    "password", "password123", "password123!", "1234567890", "qwertyuiop", "admin12345",
    "welcome123", "letmein123", "iloveyou123", "monkey1234", "dragon1234",
    "password1234", "pass123456", "abc1234567", "stegchat123", "trustnoone1",
}

class PasswordPolicyError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)

def validate_password_policy(password: str) -> str:
    """Validate password against length, complexity, common list, and handle bcrypt 72-byte limit.
    
    Returns:
        Prepared password string for hashing (pre-hashed with SHA-256 + base64 if >= 72 bytes).
    """
    if len(password) < 10:
        raise PasswordPolicyError("Password must be at least 10 characters long.")

    if not re.search(r"[A-Z]", password):
        raise PasswordPolicyError("Password must contain at least one uppercase letter.")

    if not re.search(r"[a-z]", password):
        raise PasswordPolicyError("Password must contain at least one lowercase letter.")

    if not re.search(r"\d", password):
        raise PasswordPolicyError("Password must contain at least one number.")

    if password.lower() in COMMON_PASSWORDS:
        raise PasswordPolicyError("Password is too common or easily guessable. Please choose a more secure password.")

    # Bcrypt 72-byte limit handling:
    # If password utf-8 length >= 72 bytes, pre-hash with SHA-256 and encode to Base64 (44 chars)
    # This prevents silent truncation while safely supporting arbitrary-length passphrases.
    if len(password.encode("utf-8")) >= 72:
        digest = hashlib.sha256(password.encode("utf-8")).digest()
        return base64.b64encode(digest).decode("ascii")

    return password

# ---------------------------------------------------------------------------
# In-Memory Sliding Window Rate Limiter
# ---------------------------------------------------------------------------

class RateLimiter:
    """Sliding-window rate limiter per key (IP address or account identifier)."""

    def __init__(self):
        # Maps key -> list of timestamp floats
        self._records: Dict[str, list[float]] = {}
        # Maps key -> lockout expiry timestamp
        self._lockouts: Dict[str, float] = {}

    def check_rate_limit(self, key: str, max_attempts: int = 5, window_seconds: int = 60, lockout_seconds: int = 300) -> None:
        if os.getenv("DISABLE_RATE_LIMITER", "false").lower() in ("true", "1"):
            return
        now = time.time()

        # Check existing lockout
        if key in self._lockouts:
            if now < self._lockouts[key]:
                remaining = int(self._lockouts[key] - now)
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many attempts. Account/IP temporarily locked. Please try again in {remaining} seconds.",
                )
            else:
                del self._lockouts[key]

        # Clean old timestamps
        timestamps = [t for t in self._records.get(key, []) if now - t < window_seconds]
        if len(timestamps) >= max_attempts:
            # Trigger lockout
            self._lockouts[key] = now + lockout_seconds
            self._records[key] = []
            raise HTTPException(
                status_code=429,
                detail=f"Too many attempts. Rate limit exceeded. Locked out for {lockout_seconds} seconds.",
            )

        timestamps.append(now)
        self._records[key] = timestamps

    def reset(self, key: str) -> None:
        self._records.pop(key, None)
        self._lockouts.pop(key, None)

auth_rate_limiter = RateLimiter()
