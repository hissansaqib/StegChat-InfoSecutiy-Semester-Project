"""Crypto information and algorithm catalog router."""

from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from ..crypto import SUPPORTED_ALGORITHMS, get_at_rest_cipher

router = APIRouter(tags=["crypto"])

class CryptoAlgorithmInfo(BaseModel):
    id: str
    name: str
    key_size_bytes: int
    nonce_size_bytes: int
    tag_size_bytes: int
    standard: str
    notes: str

class CryptoSettingsResponse(BaseModel):
    algorithms: List[CryptoAlgorithmInfo]
    active_key_id: str
    tier_info: Dict[str, str]

@router.get("/crypto/algorithms", response_model=List[CryptoAlgorithmInfo], summary="List supported cryptographic ciphers")
def list_algorithms() -> List[CryptoAlgorithmInfo]:
    """List all supported AEAD cryptographic ciphers for payload encryption."""
    return [CryptoAlgorithmInfo(**v) for v in SUPPORTED_ALGORITHMS.values()]

@router.get("/crypto/settings", response_model=CryptoSettingsResponse, summary="Get cryptographic status and tiers")
def get_crypto_settings() -> CryptoSettingsResponse:
    """Return active key ID, supported algorithms, and multi-tier security breakdown."""
    arc = get_at_rest_cipher()
    algs = [CryptoAlgorithmInfo(**v) for v in SUPPORTED_ALGORITHMS.values()]
    return CryptoSettingsResponse(
        algorithms=algs,
        active_key_id=arc.active_key_id,
        tier_info={
            "tier_1": "Server-Readable At-Rest Encryption (AES-256-GCM / ChaCha20-Poly1305 with STEGCHAT_MASTER_KEY). Protects against raw database dump exfiltration and cloud volume compromise.",
            "tier_2": "Browser-Encrypted Lab/Covert Steganography (End-to-End or HKDF-derived secret key). The plaintext is never visible in the clear to the backend database.",
        },
    )

