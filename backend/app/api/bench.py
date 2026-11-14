"""Benchmarking API router with selectable cryptographic ciphers."""

import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..carriers import get_carrier
from ..crypto import LabCipher, CryptoEnvelope

router = APIRouter(tags=["bench"])

_BENCH_HISTORY: List[Dict[str, Any]] = []

class BenchRunRequest(BaseModel):
    carrier_id: str
    payload_size: int = Field(64, gt=0)
    iterations: int = Field(3, gt=0, le=20)
    name: str = "Benchmark Suite"
    algorithm: Optional[str] = "aes-256-gcm"
    seed: Optional[str] = "bench_seed_pcg64_deterministic"

@router.post("/bench/run")
def run_benchmark(req: BenchRunRequest):
    try:
        carrier = get_carrier(req.carrier_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Carrier '{req.carrier_id}' not found")

    raw_payload = b"X" * req.payload_size
    seed = req.seed
    alg = (req.algorithm or "aes-256-gcm").lower()

    lab_cipher = LabCipher(ikm="stegchat-bench-seed")

    embed_times = []
    extract_times = []
    crypto_times = []
    recovered_count = 0
    stego_size = 0
    cover = b""

    for _ in range(req.iterations):
        t_c0 = time.perf_counter()
        envelope = lab_cipher.encrypt(raw_payload, alg=alg)
        envelope_bytes = envelope.to_compact_json().encode("utf-8")
        crypto_times.append((time.perf_counter() - t_c0) * 1000)

        t0 = time.perf_counter()
        stego = carrier.embed(cover=cover, payload=envelope_bytes, params={"seed": seed})
        embed_times.append((time.perf_counter() - t0) * 1000)
        stego_size = len(stego)

        t1 = time.perf_counter()
        try:
            extracted_env_bytes = carrier.extract(stego=stego, params={"seed": seed})
            envelope_obj = CryptoEnvelope.from_string(extracted_env_bytes.decode("utf-8"))
            decrypted = lab_cipher.decrypt(envelope_obj)
            extract_times.append((time.perf_counter() - t1) * 1000)
            if decrypted == raw_payload:
                recovered_count += 1
        except Exception:
            extract_times.append((time.perf_counter() - t1) * 1000)

    mean_embed = sum(embed_times) / max(1, len(embed_times))
    mean_extract = sum(extract_times) / max(1, len(extract_times))
    recovery_rate = recovered_count / req.iterations

    run_id = str(uuid.uuid4())
    result = {
        "id": run_id,
        "name": req.name,
        "carrier_id": req.carrier_id,
        "algorithm": alg,
        "payload_size": req.payload_size,
        "carrier_size": stego_size,
        "iterations": req.iterations,
        "recovery_rate": round(recovery_rate, 4),
        "embed_time_ms_mean": round(mean_embed, 2),
        "extract_time_ms_mean": round(mean_extract, 2),
        "crypto_overhead_ms": round(sum(crypto_times) / max(1, len(crypto_times)), 3),
        "total_time_ms": round(mean_embed + mean_extract, 2),
        "status": "completed",
    }
    _BENCH_HISTORY.append(result)
    return result

@router.get("/bench/suites")
def list_suites():
    return _BENCH_HISTORY
