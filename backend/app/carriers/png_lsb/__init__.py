"""PNG LSB Carrier implementing the unified Carrier contract."""

from __future__ import annotations

import io
import math
from typing import Any, Dict, Optional
import numpy as np
from PIL import Image

from ...core.carrier import (
    Carrier,
    CarrierInfo,
    CarrierKind,
    CapacityExceeded,
    UnsupportedFormat,
    ExtractionFailed,
    CorruptCarrier,
)
from ...core.frame import (
    build_frame,
    parse_frame,
    read_frame_length,
    generate_positions,
    FRAME_OVERHEAD,
)

class PngLsbCarrier(Carrier):
    """PNG LSB Carrier with PRNG position dispersion and shared frame packaging."""

    @property
    def info(self) -> CarrierInfo:
        return CarrierInfo(
            id="png_lsb",
            kind=CarrierKind.IMAGE,
            display_name="PNG Lossless Image LSB Carrier",
            accepted_mime=["image/png"],
            output_mime="image/png",
            deliverable=True,
            modes_schema={
                "type": "object",
                "properties": {
                    "channels": {
                        "type": "string",
                        "enum": ["RGB", "RGBA"],
                        "default": "RGB",
                        "description": "Pixel channels to modulate",
                    }
                },
            },
            limitations=[
                "Lossless formats only (PNG). JPEG compression will destroy payload.",
                "Capacity bounded by (width * height * channels) / 8 bytes.",
            ],
            version="1.0.0",
        )

    def validate(self, data: bytes) -> bool:
        if len(data) < 8 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            return False
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
            return True
        except Exception:
            return False

    def capacity(self, data: bytes, options: Optional[Dict[str, Any]] = None) -> int:
        if not data or not self.validate(data):
            # Synthetic canvas fallback assumption: minimum 64x64 RGB = 4096 * 3 bits = 1536 bytes
            total_slots = 64 * 64 * 3
            return max(0, (total_slots // 8) - FRAME_OVERHEAD)

        try:
            with Image.open(io.BytesIO(data)) as img:
                w, h = img.size
                channels = 3 if img.mode != "RGBA" else 4
                total_bits = w * h * channels
                max_bytes = total_bits // 8
                return max(0, max_bytes - FRAME_OVERHEAD)
        except Exception:
            return 0

    def embed(self, cover: bytes, payload: bytes, params: Optional[Dict[str, Any]] = None) -> bytes:
        params = params or {}
        seed = params.get("seed") if isinstance(params, dict) else getattr(params, "seed", None)

        frame = build_frame(payload, seed)
        frame_bits = []
        for b in frame:
            for bit_pos in range(7, -1, -1):
                frame_bits.append((b >> bit_pos) & 1)
        needed_bits = len(frame_bits)

        # Load or generate cover image
        if cover and self.validate(cover):
            try:
                img = Image.open(io.BytesIO(cover)).convert("RGB")
            except Exception as e:
                raise UnsupportedFormat(f"Failed to decode PNG cover: {e}") from e
        else:
            # Generate synthetic cover
            min_pixels = (needed_bits + 2) // 3
            side = max(64, int(math.ceil(math.sqrt(min_pixels))) + 8)
            img = Image.new("RGB", (side, side), color=(70, 95, 120))

        arr = np.array(img, dtype=np.uint8)
        total_slots = arr.size  # total channel bytes

        if needed_bits > total_slots:
            raise CapacityExceeded(
                f"Payload requiring {needed_bits} bits exceeds container capacity ({total_slots} bits)",
                available=total_slots // 8,
                required=len(frame),
            )

        # Pseudorandom slot allocation
        slots = generate_positions(seed, total_slots, needed_bits)
        flat = arr.ravel()

        mask_u8 = np.uint8(0xFE)
        for slot_idx, bit_val in zip(slots, frame_bits):
            flat[slot_idx] = (flat[slot_idx] & mask_u8) | np.uint8(bit_val)

        out_img = Image.fromarray(arr, mode="RGB")
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        return buf.getvalue()

    def extract(self, stego: bytes, params: Optional[Dict[str, Any]] = None) -> bytes:
        if not self.validate(stego):
            raise UnsupportedFormat("Input is not a valid PNG image")

        params = params or {}
        seed = params.get("seed") if isinstance(params, dict) else getattr(params, "seed", None)

        try:
            img = Image.open(io.BytesIO(stego)).convert("RGB")
            arr = np.array(img, dtype=np.uint8)
            flat = arr.ravel()
            total_slots = arr.size
        except Exception as e:
            raise CorruptCarrier(f"Failed to read PNG image pixels: {e}") from e

        # First read 4 bytes (32 bits) to find payload length
        if total_slots < 32:
            raise ExtractionFailed("Carrier too small to hold header")

        header_slots = generate_positions(seed, total_slots, 32)
        header_bits = [int(flat[idx] & 1) for idx in header_slots]

        header_bytes = bytearray()
        for i in range(0, 32, 8):
            b = 0
            for bit in header_bits[i : i + 8]:
                b = (b << 1) | bit
            header_bytes.append(b)

        try:
            payload_len = read_frame_length(bytes(header_bytes), seed)
        except Exception as e:
            raise ExtractionFailed(f"Failed to parse frame length header: {e}") from e

        total_frame_bytes = payload_len + FRAME_OVERHEAD
        total_frame_bits = total_frame_bytes * 8

        if total_frame_bits > total_slots or payload_len < 0:
            raise ExtractionFailed(
                f"Extracted payload length ({payload_len} bytes) exceeds carrier capacity. Incorrect seed or corrupted carrier."
            )

        all_slots = generate_positions(seed, total_slots, total_frame_bits)
        all_bits = [int(flat[idx] & 1) for idx in all_slots]

        frame_bytes = bytearray()
        for i in range(0, total_frame_bits, 8):
            b = 0
            for bit in all_bits[i : i + 8]:
                b = (b << 1) | bit
            frame_bytes.append(b)

        try:
            return parse_frame(bytes(frame_bytes), seed)
        except Exception as e:
            raise ExtractionFailed(f"PNG LSB frame verification failed: {e}") from e

    def measure(self, cover: bytes, stego: bytes) -> Dict[str, Any]:
        try:
            c_img = Image.open(io.BytesIO(cover)).convert("RGB")
            s_img = Image.open(io.BytesIO(stego)).convert("RGB")
            c_arr = np.array(c_img, dtype=np.float64)
            s_arr = np.array(s_img, dtype=np.float64)

            mse = float(np.mean((c_arr - s_arr) ** 2))
            psnr = 100.0 if mse == 0 else float(10 * math.log10((255.0 ** 2) / mse))
            return {
                "mse": round(mse, 4),
                "psnr_db": round(psnr, 2),
                "fidelity": max(0.0, min(1.0, psnr / 100.0)),
            }
        except Exception:
            return {"mse": 0.0, "psnr_db": 99.0, "fidelity": 1.0}

    def features(self, data: bytes) -> Dict[str, Any]:
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            arr = np.array(img, dtype=np.uint8)
            lsb = arr & 1
            even_ratio = float(np.mean(lsb == 0))
            return {
                "width": img.width,
                "height": img.height,
                "lsb_zero_ratio": round(even_ratio, 4),
            }
        except Exception:
            return {"error": "Invalid PNG"}
