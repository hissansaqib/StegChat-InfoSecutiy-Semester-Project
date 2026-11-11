from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import base64
from typing import List

from ..core.errors import NotImplementedError
from ..core.schemas import CarrierPayload, CarrierResult
from ..carriers import get_carrier, list_carriers

router = APIRouter()

@router.get("/carriers", summary="List available carriers")
def list_available_carriers() -> List[str]:
    return list_carriers()

@router.post("/carriers/{carrier_id}/embed", response_model=CarrierResult, summary="Embed payload using carrier")
def embed_payload(carrier_id: str, payload: CarrierPayload):
    try:
        carrier_cls = get_carrier(carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{carrier_id}' not found")
    carrier = carrier_cls()
    payload_bytes = base64.b64decode(payload.payload)
    key_bytes = base64.b64decode(payload.key)
    carrier_bytes = carrier.embed(payload_bytes, key_bytes)
    carrier_b64 = base64.b64encode(carrier_bytes).decode()
    return CarrierResult(carrier_bytes=carrier_b64)

@router.post("/carriers/{carrier_id}/extract", response_model=CarrierResult, summary="Extract payload from carrier")
def extract_payload(carrier_id: str, payload: CarrierPayload):
    try:
        carrier_cls = get_carrier(carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{carrier_id}' not found")
    carrier = carrier_cls()
    carrier_bytes = base64.b64decode(payload.payload)  # here payload field holds carrier bytes
    key_bytes = base64.b64decode(payload.key)
    extracted = carrier.extract(carrier_bytes, key_bytes)
    extracted_b64 = base64.b64encode(extracted).decode()
    return CarrierResult(carrier_bytes=extracted_b64)

