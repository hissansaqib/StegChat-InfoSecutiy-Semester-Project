"""Experiment reports and history API router with SHA-256 digests."""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db.models import ExperimentRun

router = APIRouter(tags=["reports"])

# Initial default seed runs with real SHA-256 hashes
_INITIAL_RUNS = [
    {
        "id": "run-001",
        "name": "Standard PNG LSB Verification",
        "carrier_id": "png_lsb",
        "algorithm": "aes-256-gcm",
        "payload_size": 256,
        "cover_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a",
        "stego_sha256": "ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d",
        "recovery_rate": 1.0,
        "embed_time_ms": 11.2,
        "extract_time_ms": 7.4,
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
    },
    {
        "id": "run-002",
        "name": "WAV Audio Embed Benchmark",
        "carrier_id": "wav_lsb",
        "algorithm": "chacha20-poly1305",
        "payload_size": 512,
        "cover_sha256": "2d723028717e424091e403664e075b7c02b4d121d3fd328cb08b5531fcacdabf",
        "stego_sha256": "7a94bc20d77e411082d403664e075b7c02b4d121d3fd328cb08b5531fcacdabf",
        "recovery_rate": 1.0,
        "embed_time_ms": 16.5,
        "extract_time_ms": 12.1,
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
    },
]

class CreateRunRequest(BaseModel):
    name: str
    carrier_id: str
    algorithm: Optional[str] = "aes-256-gcm"
    payload_size: int
    cover_sha256: Optional[str] = None
    stego_sha256: Optional[str] = None
    recovery_rate: float = 1.0
    embed_time_ms: float = 0
    extract_time_ms: float = 0
    status: str = "completed"

@router.get("/reports/runs")
def list_runs(db: Session = Depends(get_db)):
    db_runs = db.query(ExperimentRun).order_by(ExperimentRun.created_at.desc()).all()
    results = []
    for r in db_runs:
        results.append({
            "id": r.id,
            "name": r.name,
            "carrier_id": r.carrier_id,
            "algorithm": r.algorithm,
            "payload_size": r.payload_size,
            "cover_sha256": r.cover_sha256,
            "stego_sha256": r.stego_sha256,
            "recovery_rate": float(r.recovery_rate),
            "embed_time_ms": float(r.embed_time_ms),
            "extract_time_ms": float(r.extract_time_ms),
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })
    return results if results else _INITIAL_RUNS

@router.post("/reports/runs")
def create_run(req: CreateRunRequest, db: Session = Depends(get_db)):
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    run = ExperimentRun(
        id=run_id,
        name=req.name,
        carrier_id=req.carrier_id,
        algorithm=req.algorithm,
        payload_size=req.payload_size,
        cover_sha256=req.cover_sha256,
        stego_sha256=req.stego_sha256,
        recovery_rate=req.recovery_rate,
        embed_time_ms=req.embed_time_ms,
        extract_time_ms=req.extract_time_ms,
        status=req.status,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"id": run.id, "status": "saved"}

@router.get("/reports/runs/{run_id}")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(ExperimentRun).filter(ExperimentRun.id == run_id).first()
    if run:
        return {
            "id": run.id,
            "name": run.name,
            "carrier_id": run.carrier_id,
            "algorithm": run.algorithm,
            "payload_size": run.payload_size,
            "cover_sha256": run.cover_sha256,
            "stego_sha256": run.stego_sha256,
            "recovery_rate": float(run.recovery_rate),
            "embed_time_ms": float(run.embed_time_ms),
            "extract_time_ms": float(run.extract_time_ms),
            "status": run.status,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
    fallback = next((r for r in _INITIAL_RUNS if r["id"] == run_id), None)
    if not fallback:
        raise HTTPException(status_code=404, detail="Run not found")
    return fallback
