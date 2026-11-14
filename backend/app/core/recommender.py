"""Transparent recommender based on benchmark aggregates.

The recommender never imports concrete carrier implementations; it works solely on the
aggregated statistics produced by the bench module (see `backend/app/core/bench.py`).
"""

from __future__ import annotations

from typing import Dict, List, Any, Tuple, Optional

from pydantic import BaseModel, Field, validator

# ---------------------------------------------------------------------------
# Constraint schema (pydantic model)
# ---------------------------------------------------------------------------
class ConstraintWeights(BaseModel):
    recovery: float = Field(1.0, ge=0)
    fidelity: float = Field(1.0, ge=0)
    speed: float = Field(1.0, ge=0)
    overhead: float = Field(1.0, ge=0)
    capacity_margin: float = Field(1.0, ge=0)

    @validator("*", pre=True)
    def non_negative(cls, v):
        if v < 0:
            raise ValueError("weights must be non‑negative")
        return v

class RecommenderConstraints(BaseModel):
    payload_bytes: int = Field(..., gt=0)
    max_carrier_bytes: Optional[int] = None
    min_recovery_rate: float = Field(0.99, ge=0, le=1)
    max_total_ms: Optional[float] = None
    min_fidelity: Optional[float] = None  # 0‑1 normalised
    allowed_kinds: Optional[List[str]] = None  # e.g. ["IMAGE", "AUDIO", "TEXT"]
    deliverable_only: bool = False
    weights: ConstraintWeights = Field(default_factory=ConstraintWeights)

    @validator("allowed_kinds", each_item=True)
    def normalize_kind(cls, v):
        return v.upper()

# ---------------------------------------------------------------------------
# Helper to fetch the relevant aggregate entry for a carrier at a given payload
# ---------------------------------------------------------------------------
def _interpolate_aggregate(
    agg_by_size: Dict[int, Dict[str, Any]],
    payload: int,
) -> Tuple[Dict[str, Any], bool]:
    """Return interpolated aggregate for *payload*.

    ``agg_by_size`` maps payload size (int) -> aggregated stats dict.
    If *payload* exactly matches a key, the dict is returned with ``interpolated=False``.
    If it lies between two measured sizes, a linear interpolation for numeric fields is performed
    and ``interpolated=True``.  If it lies outside the measured range, ``None`` is returned.
    """
    sizes = sorted(agg_by_size.keys())
    if not sizes:
        return None, False
    if payload in agg_by_size:
        return agg_by_size[payload], False
    # Find bounding sizes
    lo = None
    hi = None
    for s in sizes:
        if s < payload:
            lo = s
        if s > payload and hi is None:
            hi = s
            break
    if lo is None or hi is None:
        return None, False
    # Linear interpolation for each numeric field
    lo_stats = agg_by_size[lo]
    hi_stats = agg_by_size[hi]
    factor = (payload - lo) / (hi - lo)
    interpolated: Dict[str, Any] = {}
    for key, lo_val in lo_stats.items():
        hi_val = hi_stats.get(key)
        if isinstance(lo_val, (int, float)) and isinstance(hi_val, (int, float)):
            interpolated[key] = lo_val + factor * (hi_val - lo_val)
        else:
            interpolated[key] = lo_val  # non‑numeric kept from lower size
    return interpolated, True

# ---------------------------------------------------------------------------
# Main recommendation function
# ---------------------------------------------------------------------------
def recommend(constraints: RecommenderConstraints, aggregates: Dict[Tuple[str, int], Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a ranking based solely on stored benchmark aggregates.

    ``aggregates`` is the output of ``bench.aggregate``: a mapping
    ``(carrier_id, payload_size) -> stats`` where ``stats`` contains numeric
    aggregates such as ``recovery_rate_mean``, ``ssim_mean`` etc.
    """
    # 1. Group aggregates by carrier
    carrier_groups: Dict[str, Dict[int, Dict[str, Any]]] = {}
    carrier_info: Dict[str, Dict[str, Any]] = {}
    for (carrier_id, size), stats in aggregates.items():
        carrier_groups.setdefault(carrier_id, {})[size] = stats
        # store carrier kind & deliverable flag if present in stats (added by bench)
        carrier_info.setdefault(carrier_id, {})
        carrier_info[carrier_id].setdefault("kind", stats.get("kind"))
        carrier_info[carrier_id].setdefault("deliverable", stats.get("deliverable", False))
        carrier_info[carrier_id].setdefault("max_capacity_bytes", stats.get("capacity_bytes_mean"))

    survivors: List[Dict[str, Any]] = []
    violations: List[Dict[str, Any]] = []

    # 2. Hard filters
    for carrier_id, size_map in carrier_groups.items():
        info = carrier_info[carrier_id]
        # Kind filter
        if constraints.allowed_kinds and info.get("kind") not in constraints.allowed_kinds:
            violations.append({"carrier": carrier_id, "reason": "kind not allowed"})
            continue
        # Deliverable filter
        if constraints.deliverable_only and not info.get("deliverable"):
            violations.append({"carrier": carrier_id, "reason": "not deliverable"})
            continue
        # Capacity filter
        max_cap = info.get("max_capacity_bytes")
        if max_cap is not None:
            if constraints.max_carrier_bytes and max_cap < constraints.max_carrier_bytes:
                violations.append({"carrier": carrier_id, "reason": "capacity below max_carrier_bytes"})
                continue
            if max_cap < constraints.payload_bytes:
                violations.append({"carrier": carrier_id, "reason": "payload exceeds capacity"})
                continue
        # Get nearest aggregate (interpolated if possible)
        agg_entry, interpolated = _interpolate_aggregate(size_map, constraints.payload_bytes)
        if agg_entry is None:
            violations.append({"carrier": carrier_id, "reason": "no measurement for payload size"})
            continue
        # Apply soft constraints (recovery, speed, fidelity, overhead)
        # Recovery rate
        rec_rate = agg_entry.get("recovery_rate_mean")
        if rec_rate is None or rec_rate < constraints.min_recovery_rate:
            violations.append({"carrier": carrier_id, "reason": "recovery_rate too low", "value": rec_rate})
            continue
        # Total time (embed + extract)
        total_ms = agg_entry.get("embed_ms_mean", 0) + agg_entry.get("extract_ms_mean", 0)
        if constraints.max_total_ms is not None and total_ms > constraints.max_total_ms:
            violations.append({"carrier": carrier_id, "reason": "total_ms exceeds limit", "value": total_ms})
            continue
        # Fidelity (kind‑specific)
        kind = info.get("kind")
        fidelity = None
        if kind == "IMAGE":
            # prefer SSIM, fallback to normalised PSNR (scaled to 0‑1)
            if "ssim_mean" in agg_entry:
                fidelity = agg_entry["ssim_mean"]  # already 0‑1
            elif "psnr_mean" in agg_entry:
                # PSNR can be large; normalise by dividing by a high ceiling (e.g., 60 dB)
                fidelity = min(1.0, agg_entry["psnr_mean"] / 60.0)
        elif kind == "AUDIO":
            if "snr_db_mean" in agg_entry:
                fidelity = min(1.0, agg_entry["snr_db_mean"] / 60.0)
        elif kind == "TEXT":
            if "similarity_ratio_mean" in agg_entry:
                fidelity = agg_entry["similarity_ratio_mean"]
        if fidelity is None:
            # No fidelity metric → treat as 0 (cannot satisfy min_fidelity)
            fidelity = 0.0
        if constraints.min_fidelity is not None and fidelity < constraints.min_fidelity:
            violations.append({"carrier": carrier_id, "reason": "fidelity too low", "value": fidelity})
            continue
        # Overhead (size_overhead_bytes_mean per payload byte)
        overhead_bytes = agg_entry.get("size_overhead_bytes_mean", 0)
        overhead_ratio = overhead_bytes / max(1, constraints.payload_bytes)
        # Capacity margin
        capacity_margin = (info.get("max_capacity_bytes", 0) - constraints.payload_bytes) / max(1, constraints.payload_bytes)

        survivors.append({
            "carrier_id": carrier_id,
            "kind": kind,
            "interpolated": interpolated,
            "recovery_rate": rec_rate,
            "fidelity": fidelity,
            "total_ms": total_ms,
            "overhead_ratio": overhead_ratio,
            "capacity_margin": capacity_margin,
            "raw_metrics": agg_entry,
        })

    if not survivors:
        return {"status": "needs_benchmark", "violations": violations}

    # 3. Normalise criteria across survivors (min‑max)
    def _minmax(values: List[float]) -> Tuple[float, float]:
        return (min(values), max(values))

    # Prepare lists
    rec_vals = [s["recovery_rate"] for s in survivors]
    fid_vals = [s["fidelity"] for s in survivors]
    spd_vals = [s["total_ms"] for s in survivors]
    oh_vals = [s["overhead_ratio"] for s in survivors]
    cap_vals = [s["capacity_margin"] for s in survivors]

    rec_min, rec_max = _minmax(rec_vals)
    fid_min, fid_max = _minmax(fid_vals)
    spd_min, spd_max = _minmax(spd_vals)
    oh_min, oh_max = _minmax(oh_vals)
    cap_min, cap_max = _minmax(cap_vals)

    def _norm(val, vmin, vmax, invert=False):
        if vmax == vmin:
            return 1.0  # all equal → neutral
        norm = (val - vmin) / (vmax - vmin)
        return 1 - norm if invert else norm

    # 4. Weighted sum
    rankings = []
    for s in survivors:
        norm_rec = _norm(s["recovery_rate"], rec_min, rec_max)
        norm_fid = _norm(s["fidelity"], fid_min, fid_max)
        norm_spd = _norm(s["total_ms"], spd_min, spd_max, invert=True)  # lower time better
        norm_oh = _norm(s["overhead_ratio"], oh_min, oh_max, invert=True)
        norm_cap = _norm(s["capacity_margin"], cap_min, cap_max, invert=False)
        # contributions map for UI
        contributions = {
            "recovery": norm_rec,
            "fidelity": norm_fid,
            "speed": norm_spd,
            "overhead": norm_oh,
            "capacity_margin": norm_cap,
        }
        weighted_score = (
            constraints.weights.recovery * norm_rec
            + constraints.weights.fidelity * norm_fid
            + constraints.weights.speed * norm_spd
            + constraints.weights.overhead * norm_oh
            + constraints.weights.capacity_margin * norm_cap
        )
        rankings.append({
            "carrier_id": s["carrier_id"],
            "kind": s["kind"],
            "score": weighted_score,
            "interpolated": s["interpolated"],
            "contributions": contributions,
            "raw_metrics": s["raw_metrics"],
        })

    rankings.sort(key=lambda x: x["score"], reverse=True)

    # Snapshot hash – collect run ids from aggregates if present
    run_ids = []
    for key in aggregates.keys():
        if isinstance(key, tuple) and len(key) == 2:
            # aggregates may include a special entry "bench_snapshot_hash"
            continue
    snapshot_hash = aggregates.get("bench_snapshot_hash")

    return {
        "status": "ok",
        "ranking": rankings,
        "violations": violations,
        "bench_snapshot_hash": snapshot_hash,
    }

