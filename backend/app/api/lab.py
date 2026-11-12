"""Lab experiments API router with selectable ciphers and LabCipher."""

import base64
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..carriers import get_carrier
from ..core.carrier import CapacityExceeded, UnsupportedFormat, ExtractionFailed
from ..crypto import LabCipher, CryptoEnvelope, UnknownAlgorithmError, CryptoDecryptionError

router = APIRouter(tags=["lab"])

class LabEmbedRequest(BaseModel):
    carrier_id: str
    message: str
    algorithm: Optional[str] = "aes-256-gcm"  # aes-256-gcm or chacha20-poly1305
    passphrase: Optional[str] = None
    seed: Optional[str] = None

class LabExtractRequest(BaseModel):
    carrier_id: str
    carrier_bytes: str
    passphrase: Optional[str] = None
    seed: Optional[str] = None

@router.post("/lab/embed")
def lab_embed(req: LabEmbedRequest):
    try:
        carrier = get_carrier(req.carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{req.carrier_id}' not found")

    raw_message = req.message.encode("utf-8")
    passphrase = req.passphrase or "stegchat-lab-default-secret-seed"
    seed = req.seed or passphrase

    # 1. Encrypt message payload using LabCipher (HKDF derived key) with selected cipher algorithm
    lab_cipher = LabCipher(ikm=passphrase)
    alg = (req.algorithm or "aes-256-gcm").lower().strip()
    try:
        envelope = lab_cipher.encrypt(raw_message, alg=alg, aad=req.carrier_id.encode("utf-8"))
    except UnknownAlgorithmError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Envelope serialized to compact bytes to embed into carrier
    envelope_bytes = envelope.to_compact_json().encode("utf-8")

    t0 = time.perf_counter()
    try:
        stego_bytes = carrier.embed(
            cover=b"",
            payload=envelope_bytes,
            params={"seed": seed},
        )
    except CapacityExceeded as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnsupportedFormat as e:
        raise HTTPException(status_code=415, detail=str(e))

    duration_ms = (time.perf_counter() - t0) * 1000

    return {
        "status": "success",
        "carrier_id": req.carrier_id,
        "algorithm": envelope.alg,
        "key_id": envelope.key_id,
        "payload_size": len(raw_message),
        "envelope_size": len(envelope_bytes),
        "carrier_size": len(stego_bytes),
        "embed_time_ms": round(duration_ms, 2),
        "carrier_bytes": base64.b64encode(stego_bytes).decode("ascii"),
    }

@router.post("/lab/extract")
def lab_extract(req: LabExtractRequest):
    try:
        carrier = get_carrier(req.carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{req.carrier_id}' not found")

    try:
        stego_bytes = base64.b64decode(req.carrier_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 in carrier_bytes")

    passphrase = req.passphrase or "stegchat-lab-default-secret-seed"
    seed = req.seed or passphrase

    t0 = time.perf_counter()
    try:
        extracted_frame_payload = carrier.extract(stego=stego_bytes, params={"seed": seed})
    except ExtractionFailed as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Extraction error: {e}")

    duration_ms = (time.perf_counter() - t0) * 1000

    # 2. Decrypt extracted envelope using LabCipher
    lab_cipher = LabCipher(ikm=passphrase)
    try:
        envelope = CryptoEnvelope.from_string(extracted_frame_payload.decode("utf-8"))
        plaintext_bytes = lab_cipher.decrypt(envelope, aad=req.carrier_id.encode("utf-8"))
        decrypted_text = plaintext_bytes.decode("utf-8", errors="replace")
        used_alg = envelope.alg
    except Exception as e:
        # Fallback if unencrypted raw payload was embedded
        try:
            decrypted_text = extracted_frame_payload.decode("utf-8")
            used_alg = "none"
        except Exception:
            raise HTTPException(status_code=400, detail=f"Envelope decryption failed: {e}")

    return {
        "status": "success",
        "carrier_id": req.carrier_id,
        "algorithm": used_alg,
        "extracted_size": len(extracted_frame_payload),
        "extract_time_ms": round(duration_ms, 2),
        "message": decrypted_text,
    }
