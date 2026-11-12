"""Fake Carrier implementing the unified Carrier contract.

Reference baseline used for testing and pipeline validation.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional
from ...core.carrier import (
    Carrier,
    CarrierInfo,
    CarrierKind,
    CapacityExceeded,
    UnsupportedFormat,
    ExtractionFailed,
)
from ...core.frame import build_frame, parse_frame, FRAME_OVERHEAD

class FakeCarrier(Carrier):
    """XOR-based testing carrier implementing full single contract."""

    @property
    def info(self) -> CarrierInfo:
        return CarrierInfo(
            id="fake",
            kind=CarrierKind.TEXT,
            display_name="Fake Baseline Carrier",
            accepted_mime=["text/plain", "application/octet-stream"],
            output_mime="application/octet-stream",
            deliverable=False,
            modes_schema={
                "type": "object",
                "properties": {
                    "prefix_tag": {"type": "string", "default": "FAKE:"}
                }
            },
            limitations=[
                "Provides zero perceptual camouflage",
                "Testing and mock baseline only"
            ],
            version="1.0.0",
        )

    def validate(self, data: bytes) -> bool:
        return len(data) >= 0

    def capacity(self, data: bytes, options: Optional[Dict[str, Any]] = None) -> int:
        # Fake carrier can hold arbitrary data, but simulated capacity is len(data)
        cap = max(0, len(data) - FRAME_OVERHEAD)
        # Minimum baseline of 1024 bytes if synthetic cover
        return max(1024, cap)

    def embed(self, cover: bytes, payload: bytes, params: Optional[Dict[str, Any]] = None) -> bytes:
        params = params or {}
        seed = params.get("seed") if isinstance(params, dict) else getattr(params, "seed", None)
        options = params.get("options", {}) if isinstance(params, dict) else getattr(params, "options", {})

        # Frame packaging
        frame = build_frame(payload, seed)

        if cover and len(frame) > len(cover) + 2048:
            raise CapacityExceeded(
                f"Payload frame size {len(frame)} exceeds simulated capacity",
                available=len(cover),
                required=len(frame),
            )

        # Prefix tag
        prefix = options.get("prefix_tag", "FAKE:").encode("utf-8")
        return prefix + frame

    def extract(self, stego: bytes, params: Optional[Dict[str, Any]] = None) -> bytes:
        params = params or {}
        seed = params.get("seed") if isinstance(params, dict) else getattr(params, "seed", None)
        options = params.get("options", {}) if isinstance(params, dict) else getattr(params, "options", {})

        prefix = options.get("prefix_tag", "FAKE:").encode("utf-8")
        if not stego.startswith(prefix):
            # In testing, might not have prefix if raw frame was fed
            frame_data = stego
        else:
            frame_data = stego[len(prefix):]

        try:
            return parse_frame(frame_data, seed)
        except Exception as e:
            raise ExtractionFailed(f"FakeCarrier extraction failed: {e}") from e

    def measure(self, cover: bytes, stego: bytes) -> Dict[str, Any]:
        diff = sum(abs(a - b) for a, b in zip(cover, stego))
        return {
            "byte_diff": diff,
            "fidelity_score": 1.0 if diff == 0 else max(0.0, 1.0 - (diff / max(1, len(cover)))),
        }

    def features(self, data: bytes) -> Dict[str, Any]:
        even = sum(1 for b in data if b % 2 == 0)
        return {
            "even_ratio": even / max(1, len(data)),
            "length": len(data),
        }
