"""Zero-Width Unicode Text Carrier implementing the unified Carrier contract."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional
from ...core.carrier import (
    Carrier,
    CarrierInfo,
    CarrierKind,
    CapacityExceeded,
    UnsupportedFormat,
    ExtractionFailed,
)
from ...core.frame import (
    build_frame,
    parse_frame,
    FRAME_OVERHEAD,
)

# Zero-Width Space (\u200B) for bit 0, Zero-Width Non-Joiner (\u200C) for bit 1
ZW_ZERO = "\u200B"
ZW_ONE = "\u200C"
ZW_MAP = {ZW_ZERO: 0, ZW_ONE: 1}

DEFAULT_TEXT_COVER = "StegChat provides covert steganographic communications and information security analysis across distributed media networks."

class TextZwCarrier(Carrier):
    """Zero-width Unicode characters embedded between whitespace or characters."""

    @property
    def info(self) -> CarrierInfo:
        return CarrierInfo(
            id="text_zw",
            kind=CarrierKind.TEXT,
            display_name="Zero-Width Unicode Text Carrier",
            accepted_mime=["text/plain"],
            output_mime="text/plain",
            deliverable=True,
            modes_schema={
                "type": "object",
                "properties": {
                    "insertion_mode": {
                        "type": "string",
                        "enum": ["after_space", "end_of_text"],
                        "default": "after_space",
                    }
                },
            },
            limitations=[
                "Plain text only; rich text or copy-paste stripping non-printable chars will remove payload.",
                "Capacity dependent on cover text length or appended hidden sequence.",
            ],
            version="1.0.0",
        )

    def validate(self, data: bytes) -> bool:
        try:
            data.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    def capacity(self, data: bytes, options: Optional[Dict[str, Any]] = None) -> int:
        if not data or not self.validate(data):
            # Synthetic default capacity
            return 256

        text = data.decode("utf-8", errors="ignore")
        # In after_space mode, each space can comfortably hold 1-2 bytes (8-16 ZW chars)
        spaces = text.count(" ")
        max_bytes = max(256, (spaces * 16) // 8)
        return max(0, max_bytes - FRAME_OVERHEAD)

    def embed(self, cover: bytes, payload: bytes, params: Optional[Dict[str, Any]] = None) -> bytes:
        params = params or {}
        seed = params.get("seed") if isinstance(params, dict) else getattr(params, "seed", None)

        frame = build_frame(payload, seed)
        bits = []
        for b in frame:
            for bit_pos in range(7, -1, -1):
                bits.append((b >> bit_pos) & 1)

        zw_stream = "".join(ZW_ONE if bit else ZW_ZERO for bit in bits)

        if cover and self.validate(cover):
            cover_text = cover.decode("utf-8")
        else:
            cover_text = DEFAULT_TEXT_COVER

        # Strip any existing ZW characters from cover
        cleaned = re.sub(r"[\u200B\u200C]", "", cover_text)

        # Append or insert after first sentence
        if " " in cleaned:
            parts = cleaned.split(" ", 1)
            result_text = parts[0] + " " + zw_stream + parts[1]
        else:
            result_text = cleaned + zw_stream

        return result_text.encode("utf-8")

    def extract(self, stego: bytes, params: Optional[Dict[str, Any]] = None) -> bytes:
        if not self.validate(stego):
            raise UnsupportedFormat("Input is not valid UTF-8 text")

        params = params or {}
        seed = params.get("seed") if isinstance(params, dict) else getattr(params, "seed", None)

        text = stego.decode("utf-8", errors="replace")
        zw_chars = [c for c in text if c in ZW_MAP]

        if len(zw_chars) < 64:  # At least 8 bytes frame = 64 bits
            raise ExtractionFailed("No zero-width steganographic bitstream detected in text")

        bits = [ZW_MAP[c] for c in zw_chars]

        # Chunk into bytes
        frame_bytes = bytearray()
        for i in range(0, len(bits) - 7, 8):
            b = 0
            for bit in bits[i : i + 8]:
                b = (b << 1) | bit
            frame_bytes.append(b)

        try:
            return parse_frame(bytes(frame_bytes), seed)
        except Exception as e:
            raise ExtractionFailed(f"Text ZW frame parsing failed: {e}") from e

    def measure(self, cover: bytes, stego: bytes) -> Dict[str, Any]:
        c_text = cover.decode("utf-8", errors="ignore")
        s_text = stego.decode("utf-8", errors="ignore")
        return {
            "visible_length_diff": abs(len(re.sub(r"[\u200B\u200C]", "", s_text)) - len(c_text)),
            "zw_chars_embedded": len(re.findall(r"[\u200B\u200C]", s_text)),
            "fidelity": 1.0,
        }

    def features(self, data: bytes) -> Dict[str, Any]:
        text = data.decode("utf-8", errors="ignore")
        zw_count = len(re.findall(r"[\u200B\u200C]", text))
        return {
            "text_length": len(text),
            "zero_width_chars": zw_count,
            "has_hidden_text": zw_count > 0,
        }

