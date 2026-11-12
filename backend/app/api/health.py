from fastapi import APIRouter

router = APIRouter()

@router.get("/health", summary="Health check")
@router.get("/healthz", summary="Health check (alt)")
def health_check():
    return {"status": "ok"}

