"""Experiment reports and history API router."""

import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["reports"])

_RUNS: List[Dict[str, Any]] = [
    {
        "id": "run-001",
        "name": "Standard PNG LSB Verification",
        "carrier_id": "png_lsb",
        "created_at": datetime.utcnow().isoformat(),
        "status": "completed",
        "payload_size": 256,
        "recovery_rate": 1.0,
        "embed_time_ms": 11.2,
        "extract_time_ms": 7.4,
    },
    {
        "id": "run-002",
        "name": "WAV Audio Embed Benchmark",
        "carrier_id": "wav_lsb",
        "created_at": datetime.utcnow().isoformat(),
        "status": "completed",
        "payload_size": 512,
        "recovery_rate": 1.0,
        "embed_time_ms": 16.5,
        "extract_time_ms": 12.1,
    },
]

@router.get("/reports/runs")
def list_runs():
    return _RUNS

@router.get("/reports/runs/{run_id}")
def get_run(run_id: str):
    run = next((r for r in _RUNS if r["id"] == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
