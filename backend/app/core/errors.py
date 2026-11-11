"""Shared error handling contracts for StegChat backend.

Defines custom exceptions that can be raised in business logic and translated
into appropriate HTTP responses by FastAPI exception handlers.
"""

from fastapi import HTTPException
from typing import Any

class APIError(HTTPException):
    """Base class for API errors.

    Subclass this to create domain‑specific errors. ``status_code`` defaults to
    400 (bad request) but can be overridden.
    """

    def __init__(self, detail: Any, status_code: int = 400, headers: dict | None = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class NotImplementedError(APIError):
    """Raised for stub endpoints that are not yet implemented."""

    def __init__(self, detail: str = "Not implemented yet"):
        super().__init__(detail=detail, status_code=501)

