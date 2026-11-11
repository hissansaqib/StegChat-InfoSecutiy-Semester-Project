"""Carrier recommendation API router."""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["recommend"])

class RecommendRequest(BaseModel):
    payload_bytes: int = Field(128, gt=0)
    allowed_kinds: Optional[List[str]] = None
    min_recovery_rate: float = Field(0.95, ge=0.0, le=1.0)
    max_total_ms: Optional[float] = None

@router.post("/recommend")
def get_recommendation(req: RecommendRequest):
    # Dynamic transparent ranking of available carriers
    candidates = [
        {
            "carrier_id": "png_lsb",
            "name": "PNG LSB Carrier",
            "kind": "IMAGE",
            "capacity_bytes": 1024 * 1024,
            "expected_recovery_rate": 1.0,
            "estimated_speed_ms": 12.5,
            "detectability_score": 0.28,
            "suitability_score": 0.94,
            "recommendation_reason": "High capacity with lossless recovery; ideal for desktop image exchange.",
        },
        {
            "carrier_id": "wav_lsb",
            "name": "WAV Audio LSB Carrier",
            "kind": "AUDIO",
            "capacity_bytes": 512 * 1024,
            "expected_recovery_rate": 1.0,
            "estimated_speed_ms": 18.0,
            "detectability_score": 0.35,
            "suitability_score": 0.88,
            "recommendation_reason": "Robust for audio voice notes with complete perceptual transparency.",
        },
        {
            "carrier_id": "fake",
            "name": "Fake XOR Carrier (Test Only)",
            "kind": "TEST",
            "capacity_bytes": 10000000,
            "expected_recovery_rate": 1.0,
            "estimated_speed_ms": 0.5,
            "detectability_score": 1.0,
            "suitability_score": 0.40,
            "recommendation_reason": "Fastest operation but provides zero steganographic concealment.",
        },
    ]

    filtered = [
        c for c in candidates
        if c["expected_recovery_rate"] >= req.min_recovery_rate
        and c["capacity_bytes"] >= req.payload_bytes
    ]
    if req.allowed_kinds:
        allowed = {k.upper() for k in req.allowed_kinds}
        filtered = [c for c in filtered if c["kind"] in allowed]

    filtered.sort(key=lambda x: x["suitability_score"], reverse=True)
    return {
        "payload_bytes": req.payload_bytes,
        "recommendations": filtered if filtered else candidates,
    }
