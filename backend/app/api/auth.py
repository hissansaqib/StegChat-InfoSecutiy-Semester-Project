"""Auth router stub – returns 501 Not Implemented for all endpoints.
"""

from fastapi import APIRouter, HTTPException
from ..core.errors import NotImplementedError

router = APIRouter()

@router.get("/auth/status", summary="Auth status placeholder")
def status():
    raise NotImplementedError()

