"""PNG LSB Carrier implementation."""

from __future__ import annotations
import io
import struct
from PIL import Image
from ...core.carrier import Carrier
from .. import register

class PngLsbCarrier(Carrier):
    @property
    def id(self) -> str:
        return "png_lsb"

    @property
    def name(self) -> str:
        return "PNG LSB Carrier"

    @property
    def description(self) -> str:
        return "Least Significant Bit (LSB) embedding in PNG pixel channels with 32-bit length header."

    def embed(self, payload: bytes, key: bytes) -> bytes:
        # Prepend 4-byte length prefix
        data = struct.pack(">I", len(payload)) + payload
        data_bits = []
        for byte in data:
            for bit_pos in range(7, -1, -1):
                data_bits.append((byte >> bit_pos) & 1)

        total_bits = len(data_bits)
        # Create minimal RGB synthetic canvas if payload fits, else larger
        min_pixels = (total_bits + 2) // 3
        side = max(64, int(min_pixels ** 0.5) + 8)
        img = Image.new("RGB", (side, side), color=(73, 109, 137))
        pixels = list(img.getdata())

        new_pixels = []
        bit_idx = 0
        for r, g, b in pixels:
            channels = [r, g, b]
            for c_idx in range(3):
                if bit_idx < total_bits:
                    channels[c_idx] = (channels[c_idx] & ~1) | data_bits[bit_idx]
                    bit_idx += 1
            new_pixels.append(tuple(channels))

        out_img = Image.new("RGB", (side, side))
        out_img.putdata(new_pixels)
        buf = io.BytesIO()
        out_img.save(buf, format="PNG")
        return buf.getvalue()

    def extract(self, carrier_bytes: bytes, key: bytes) -> bytes:
        img = Image.open(io.BytesIO(carrier_bytes)).convert("RGB")
        pixels = list(img.getdata())

        bits = []
        for r, g, b in pixels:
            bits.append(r & 1)
            bits.append(g & 1)
            bits.append(b & 1)

        def bits_to_bytes(bit_list: list[int]) -> bytes:
            out = bytearray()
            for i in range(0, len(bit_list) - 7, 8):
                byte = 0
                for bit in bit_list[i:i+8]:
                    byte = (byte << 1) | bit
                out.append(byte)
            return bytes(out)

        # Read first 32 bits (4 bytes) length
        if len(bits) < 32:
            return b""
        header_bytes = bits_to_bytes(bits[:32])
        (payload_len,) = struct.unpack(">I", header_bytes)

        total_payload_bits = payload_len * 8
        if len(bits) < 32 + total_payload_bits:
            return b""

        payload_bits = bits[32 : 32 + total_payload_bits]
        return bits_to_bytes(payload_bits)

register(PngLsbCarrier)
