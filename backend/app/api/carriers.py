"""Carriers API router implementing unified contract endpoints.

- GET /carriers: Returns all registered carriers with info, options schema, limitations.
- POST /carriers/{id}/capacity: Multipart cover upload + options, returns exact capacity bytes.
- POST /carriers/{id}/embed: Embeds payload into carrier.
- POST /carriers/{id}/extract: Extracts payload from carrier.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ..carriers import get_carrier, get_all_carrier_info
from ..core.carrier import (
    CarrierInfo,
    CapacityExceeded,
    UnsupportedFormat,
    ExtractionFailed,
    CorruptCarrier,
)
from ..core.upload_validation import validate_upload

router = APIRouter(tags=["carriers"])

class CarrierPayloadRequest(BaseModel):
    payload: str = Field(..., description="Base64 encoded payload bytes to embed")
    seed: Optional[str] = Field(default=None, description="Optional seed for pseudorandom dispersion")
    options: Dict[str, Any] = Field(default_factory=dict, description="Carrier specific embedding options")
    cover: Optional[str] = Field(default=None, description="Optional Base64 encoded cover container")

class CarrierExtractRequest(BaseModel):
    carrier_bytes: str = Field(..., description="Base64 encoded stego medium")
    seed: Optional[str] = Field(default=None, description="Seed used during embedding")
    options: Dict[str, Any] = Field(default_factory=dict, description="Extraction options")

class CarrierResultResponse(BaseModel):
    carrier_bytes: str
    size: int
    carrier_id: str

class CapacityResponse(BaseModel):
    carrier_id: str
    capacity_bytes: int
    filename: Optional[str] = None
    mime_type: Optional[str] = None

@router.get("/carriers", response_model=List[CarrierInfo], summary="List available carriers and capabilities")
def list_available_carriers() -> List[CarrierInfo]:
    """Return all registered carriers with their full info, options schema, and limitations."""
    return get_all_carrier_info()

@router.post("/carriers/{carrier_id}/capacity", response_model=CapacityResponse, summary="Query exact capacity")
async def get_carrier_capacity(
    carrier_id: str,
    cover: Optional[UploadFile] = File(None),
    options: Optional[str] = Form(None),
):
    """Compute exact capacity in payload bytes for a given cover file and options."""
    try:
        carrier = get_carrier(carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{carrier_id}' not found")

    cover_bytes = b""
    safe_name = None
    mime_type = None

    if cover is not None:
        raw_data = await cover.read()
        if raw_data:
            try:
                safe_name, _, mime_type = validate_upload(raw_data, cover.filename or "cover")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            cover_bytes = raw_data

    import json
    opts = {}
    if options:
        try:
            opts = json.loads(options)
        except Exception:
            pass

    cap_bytes = carrier.capacity(cover_bytes, opts)
    return CapacityResponse(
        carrier_id=carrier_id,
        capacity_bytes=cap_bytes,
        filename=safe_name,
        mime_type=mime_type,
    )

@router.post("/carriers/{carrier_id}/embed", response_model=CarrierResultResponse, summary="Embed payload using carrier")
def embed_payload(carrier_id: str, req: CarrierPayloadRequest):
    try:
        carrier = get_carrier(carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{carrier_id}' not found")

    try:
        payload_bytes = base64.b64decode(req.payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base64 payload encoding")

    cover_bytes = b""
    if req.cover:
        try:
            cover_bytes = base64.b64decode(req.cover)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Base64 cover encoding")

    try:
        stego_bytes = carrier.embed(
            cover=cover_bytes,
            payload=payload_bytes,
            params={"seed": req.seed, "options": req.options},
        )
    except CapacityExceeded as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnsupportedFormat as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {e}")

    return CarrierResultResponse(
        carrier_bytes=base64.b64encode(stego_bytes).decode("ascii"),
        size=len(stego_bytes),
        carrier_id=carrier_id,
    )

@router.post("/carriers/{carrier_id}/extract", summary="Extract payload from carrier")
def extract_payload(carrier_id: str, req: CarrierExtractRequest):
    try:
        carrier = get_carrier(carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{carrier_id}' not found")

    try:
        stego_bytes = base64.b64decode(req.carrier_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base64 carrier encoding")

    try:
        extracted = carrier.extract(
            stego=stego_bytes,
            params={"seed": req.seed, "options": req.options},
        )
    except ExtractionFailed as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UnsupportedFormat as e:
        raise HTTPException(status_code=415, detail=str(e))
    except CorruptCarrier as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")

    return {
        "carrier_id": carrier_id,
        "extracted_payload": base64.b64encode(extracted).decode("ascii"),
        "size": len(extracted),
    }
