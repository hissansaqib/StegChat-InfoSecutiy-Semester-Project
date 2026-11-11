"""Benchmarking API router."""

import time
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..carriers import get_carrier, list_carriers

router = APIRouter(tags=["bench"])

_BENCH_HISTORY: List[Dict[str, Any]] = []

class BenchRunRequest(BaseModel):
    carrier_id: str
    payload_size: int = Field(64, gt=0)
    iterations: int = Field(3, gt=0, le=20)
    name: str = "Benchmark Suite"

@router.post("/bench/run")
def run_benchmark(req: BenchRunRequest):
    try:
        carrier_cls = get_carrier(req.carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{req.carrier_id}' not found")

    carrier = carrier_cls()
    payload = b"A" * req.payload_size
    key = b"bench_key_12345"

    embed_times = []
    extract_times = []
    recovered_count = 0
    stego_size = 0

    for _ in range(req.iterations):
        t0 = time.perf_counter()
        stego = carrier.embed(payload, key)
        embed_times.append((time.perf_counter() - t0) * 1000)
        stego_size = len(stego)

        t1 = time.perf_counter()
        extracted = carrier.extract(stego, key)
        extract_times.append((time.perf_counter() - t1) * 1000)

        if extracted == payload:
            recovered_count += 1

    mean_embed = sum(embed_times) / len(embed_times)
    mean_extract = sum(extract_times) / len(extract_times)
    recovery_rate = recovered_count / req.iterations

    run_id = str(uuid.uuid4())
    result = {
        "id": run_id,
        "name": req.name,
        "carrier_id": req.carrier_id,
        "payload_size": req.payload_size,
        "carrier_size": stego_size,
        "iterations": req.iterations,
        "recovery_rate": round(recovery_rate, 4),
        "embed_time_ms_mean": round(mean_embed, 2),
        "extract_time_ms_mean": round(mean_extract, 2),
        "total_time_ms": round(mean_embed + mean_extract, 2),
        "status": "completed",
    }
    _BENCH_HISTORY.append(result)
    return result

@router.get("/bench/suites")
def list_suites():
    return _BENCH_HISTORY
