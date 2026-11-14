"""Shared error handling contracts for StegChat backend.

Defines custom exceptions that can be raised in business logic and translated
into standard {"error": {"code", "message", "request_id"}} HTTP responses.
"""

from __future__ import annotations
from typing import Optional

class StegChatError(Exception):
    """Base class for all application domain exceptions."""
    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(self, message: str, code: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code

class CapacityExceeded(StegChatError):
    code = "CAPACITY_EXCEEDED"
    status_code = 400

    def __init__(self, message: str = "Payload exceeds carrier capacity", available: int = 0, required: int = 0):
        super().__init__(message)
        self.available = available
        self.required = required

class UnsupportedFormat(StegChatError):
    code = "UNSUPPORTED_FORMAT"
    status_code = 415

class CorruptCarrier(StegChatError):
    code = "CORRUPT_CARRIER"
    status_code = 400

class ExtractionFailed(StegChatError):
    code = "EXTRACTION_FAILED"
    status_code = 400

class AuthenticationFailed(StegChatError):
    code = "AUTHENTICATION_FAILED"
    status_code = 401

class PermissionDenied(StegChatError):
    code = "PERMISSION_DENIED"
    status_code = 403

class NotFound(StegChatError):
    code = "NOT_FOUND"
    status_code = 404

class ValidationFailed(StegChatError):
    code = "VALIDATION_FAILED"
    status_code = 422


