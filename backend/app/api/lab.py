"""Lab experiments API router."""

import base64
import time
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..carriers import get_carrier
from ..core.carrier import CapacityExceeded, UnsupportedFormat, ExtractionFailed

router = APIRouter(tags=["lab"])

class LabEmbedRequest(BaseModel):
    carrier_id: str
    message: str
    key: Optional[str] = None
    seed: Optional[str] = None

class LabExtractRequest(BaseModel):
    carrier_id: str
    carrier_bytes: str
    key: Optional[str] = None
    seed: Optional[str] = None

@router.post("/lab/embed")
def lab_embed(req: LabEmbedRequest):
    try:
        carrier = get_carrier(req.carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{req.carrier_id}' not found")

    payload_bytes = req.message.encode("utf-8")
    seed = req.seed or req.key or "stegchat_default_lab_seed"

    t0 = time.perf_counter()
    try:
        stego_bytes = carrier.embed(
            cover=b"",
            payload=payload_bytes,
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
        "payload_size": len(payload_bytes),
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

    seed = req.seed or req.key or "stegchat_default_lab_seed"

    t0 = time.perf_counter()
    try:
        extracted_bytes = carrier.extract(stego=stego_bytes, params={"seed": seed})
    except ExtractionFailed as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Extraction error: {e}")

    duration_ms = (time.perf_counter() - t0) * 1000
    extracted_text = extracted_bytes.decode("utf-8", errors="replace")

    return {
        "status": "success",
        "carrier_id": req.carrier_id,
        "extracted_size": len(extracted_bytes),
        "extract_time_ms": round(duration_ms, 2),
        "message": extracted_text,
    }
