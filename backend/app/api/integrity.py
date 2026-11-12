"""Integrity and hashing endpoints router.

Endpoints:
- POST /integrity/hash (file upload or raw text, algorithms[])
- POST /integrity/verify (file upload or raw text, expected digest, algorithm)
- POST /integrity/hmac (raw text or file upload, secret key)
- POST /integrity/hmac/verify (file or text, secret key, expected hmac)
"""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..integrity import (
    compute_data_digests,
    compute_stream_digest,
    compute_hmac_sha256,
    verify_digest,
    verify_hmac,
    SUPPORTED_DIGEST_ALGORITHMS,
)

router = APIRouter(tags=["integrity"])

class HashTextRequest(BaseModel):
    text: Optional[str] = None
    algorithms: List[str] = Field(default_factory=lambda: ["sha256", "sha512", "sha3_256", "blake2b"])

class VerifyDigestRequest(BaseModel):
    text: Optional[str] = None
    expected_digest: str
    algorithm: str = "sha256"

class HmacRequest(BaseModel):
    text: str
    key: str

class HmacVerifyRequest(BaseModel):
    text: str
    key: str
    expected_hmac: str

@router.post("/integrity/hash", summary="Compute cryptographic digests for text or uploaded file")
async def compute_hashes(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    algorithms: Optional[str] = Form(None),
):
    """Compute digests (SHA-256, SHA-512, SHA3-256, BLAKE2b) with execution duration."""
    alg_list = [a.strip() for a in algorithms.split(",")] if algorithms else ["sha256", "sha512", "sha3_256", "blake2b"]

    if file is not None:
        raw_data = await file.read()
    elif text is not None:
        raw_data = text.encode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Must provide either a file upload or text content.")

    digests = compute_data_digests(raw_data, algorithms=alg_list)
    return {
        "byte_count": len(raw_data),
        "digests": digests,
    }

@router.post("/integrity/verify", summary="Verify expected digest against file or text")
async def verify_hash(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    expected_digest: str = Form(...),
    algorithm: str = Form("sha256"),
):
    """Constant-time verification of computed digest against expected value."""
    if file is not None:
        raw_data = await file.read()
    elif text is not None:
        raw_data = text.encode("utf-8")
    else:
        raise HTTPException(status_code=400, detail="Must provide either a file upload or text content.")

    clean_alg = algorithm.lower().replace("-", "_")
    if clean_alg not in SUPPORTED_DIGEST_ALGORITHMS:
        raise HTTPException(status_code=400, detail=f"Unsupported algorithm '{algorithm}'")

    digests = compute_data_digests(raw_data, algorithms=[clean_alg])
    actual = digests[clean_alg]["digest"]
    matches = verify_digest(expected_digest, actual)

    return {
        "algorithm": clean_alg,
        "expected_digest": expected_digest.strip().lower(),
        "actual_digest": actual,
        "matches": matches,
        "byte_count": len(raw_data),
    }

@router.post("/integrity/hmac", summary="Generate HMAC-SHA256")
def generate_hmac(req: HmacRequest):
    """Generate HMAC-SHA256 given input text and secret key."""
    if not req.key:
        raise HTTPException(status_code=400, detail="HMAC key must not be empty.")
    hmac_val = compute_hmac_sha256(req.key.encode("utf-8"), req.text.encode("utf-8"))
    return {
        "algorithm": "hmac-sha256",
        "hmac": hmac_val,
        "byte_count": len(req.text.encode("utf-8")),
    }

@router.post("/integrity/hmac/verify", summary="Verify HMAC-SHA256")
def verify_hmac_endpoint(req: HmacVerifyRequest):
    """Constant-time HMAC-SHA256 verification."""
    matches = verify_hmac(
        req.key.encode("utf-8"),
        req.text.encode("utf-8"),
        req.expected_hmac,
    )
    return {
        "algorithm": "hmac-sha256",
        "matches": matches,
    }
