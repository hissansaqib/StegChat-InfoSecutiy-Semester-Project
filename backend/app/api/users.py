"""Users router stub – returns 501 Not Implemented for all endpoints.
"""

from fastapi import APIRouter
from ..core.errors import NotImplementedError

router = APIRouter()

@router.get("/users/me", summary="Current user placeholder")
def get_me():
    raise NotImplementedError()

