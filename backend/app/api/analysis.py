"""Steganalysis API router."""

import base64
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["analysis"])

_ANALYSIS_HISTORY: List[Dict[str, Any]] = []

class AnalysisRunRequest(BaseModel):
    carrier_bytes: str  # Base64
    carrier_id: str = "png_lsb"

@router.post("/analysis/run")
def run_analysis(req: AnalysisRunRequest):
    try:
        raw_bytes = base64.b64decode(req.carrier_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 carrier bytes")

    # Perform lightweight chi-square / LSB flip analysis simulation
    even_count = sum(1 for b in raw_bytes if b % 2 == 0)
    odd_count = len(raw_bytes) - even_count
    total = max(1, len(raw_bytes))
    diff = abs(even_count - odd_count)
    # Perfectly random LSBs will have diff close to 0; natural images tend to have uneven counts
    ratio = diff / total
    stego_prob = max(0.05, min(0.95, round(1.0 - (ratio * 10), 3)))

    chi_square = round(float(diff ** 2) / total, 2)
    rs_score = round(stego_prob * 0.85, 3)

    result_id = str(uuid.uuid4())
    record = {
        "id": result_id,
        "carrier_id": req.carrier_id,
        "bytes_analyzed": len(raw_bytes),
        "chi_square_stat": chi_square,
        "rs_score": rs_score,
        "stego_detected": stego_prob > 0.5,
        "detection_confidence": round(stego_prob * 100, 1),
    }
    _ANALYSIS_HISTORY.append(record)
    return record

@router.get("/analysis/results")
def list_analysis_results():
    return _ANALYSIS_HISTORY
