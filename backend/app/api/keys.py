from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import json

from ..db.models import User
from ..auth.dependencies import get_current_user

router = APIRouter(tags=["keys"])

class KdfInfo(BaseModel):
    id: str
    params: Dict[str, Any]

class KeyBundle(BaseModel):
    public_jwk: Dict[str, Any]
    wrapped_private: str  # base64
    wrapped_nonce: str    # base64 nonce used for AES-GCM wrapping
    salt: str            # base64 16‑byte salt
    kdf: KdfInfo
    fingerprint: str
    key_id: Optional[str] = Field(default="master-v1")

@router.get("/keys/me", response_model=KeyBundle, summary="Get own key bundle")
async def get_my_key_bundle(current_user: User = Depends(get_current_user)):
    if not current_user.key_bundle:
        raise HTTPException(status_code=404, detail="Key bundle not found")
    try:
        data = json.loads(current_user.key_bundle)
        return KeyBundle(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Corrupted key bundle")

@router.get("/keys/{user_id}/public", response_model=dict, summary="Get a user's public JWK and fingerprint")
async def get_user_public_key(user_id: str, current_user: User = Depends(get_current_user)):
    # Authentication required but we do not restrict who can view public keys.
    db_user = current_user.session.query(User).filter(User.id == user_id).first()
    if not db_user or not db_user.key_bundle:
        raise HTTPException(status_code=404, detail="User or key bundle not found")
    try:
        bundle = json.loads(db_user.key_bundle)
        return {"public_jwk": bundle.get("public_jwk"), "fingerprint": bundle.get("fingerprint"), "key_id": bundle.get("key_id", "master-v1")}
    except Exception:
        raise HTTPException(status_code=500, detail="Corrupted key bundle")

@router.put("/keys/bundle", response_model=KeyBundle, summary="Upload or update own key bundle (supports rotation)")
async def upload_key_bundle(bundle: KeyBundle, current_user: User = Depends(get_current_user)):
    # Store the bundle as JSON string. Overwrite existing.
    current_user.key_bundle = json.dumps(bundle.dict())
    current_user.session.add(current_user)
    current_user.session.commit()
    return bundle

