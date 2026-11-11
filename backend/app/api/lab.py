"""Lab experiments API router."""

import base64
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..carriers import get_carrier, list_carriers

router = APIRouter(tags=["lab"])

class LabEmbedRequest(BaseModel):
    carrier_id: str
    message: str
    key: str = ""

class LabExtractRequest(BaseModel):
    carrier_id: str
    carrier_bytes: str
    key: str = ""

@router.post("/lab/embed")
def lab_embed(req: LabEmbedRequest):
    try:
        carrier_cls = get_carrier(req.carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{req.carrier_id}' not found")

    carrier = carrier_cls()
    payload_bytes = req.message.encode("utf-8")
    key_bytes = req.key.encode("utf-8") if req.key else b"default_key"

    t0 = time.perf_counter()
    stego_bytes = carrier.embed(payload_bytes, key_bytes)
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
        carrier_cls = get_carrier(req.carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{req.carrier_id}' not found")

    carrier = carrier_cls()
    try:
        stego_bytes = base64.b64decode(req.carrier_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 in carrier_bytes")

    key_bytes = req.key.encode("utf-8") if req.key else b"default_key"

    t0 = time.perf_counter()
    extracted_bytes = carrier.extract(stego_bytes, key_bytes)
    duration_ms = (time.perf_counter() - t0) * 1000

    extracted_text = extracted_bytes.decode("utf-8", errors="replace")

    return {
        "status": "success",
        "carrier_id": req.carrier_id,
        "extracted_size": len(extracted_bytes),
        "extract_time_ms": round(duration_ms, 2),
        "message": extracted_text,
    }
