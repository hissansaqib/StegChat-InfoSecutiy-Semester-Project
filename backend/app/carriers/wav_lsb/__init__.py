"""WAV LSB Carrier implementation."""

from __future__ import annotations
import io
import wave
import struct
from ...core.carrier import Carrier
from .. import register

class WavLsbCarrier(Carrier):
    @property
    def id(self) -> str:
        return "wav_lsb"

    @property
    def name(self) -> str:
        return "WAV Audio LSB Carrier"

    @property
    def description(self) -> str:
        return "Least Significant Bit (LSB) embedding in 16-bit uncompressed audio frames."

    def embed(self, payload: bytes, key: bytes) -> bytes:
        data = struct.pack(">I", len(payload)) + payload
        data_bits = []
        for byte in data:
            for bit_pos in range(7, -1, -1):
                data_bits.append((byte >> bit_pos) & 1)

        total_bits = len(data_bits)
        # Create minimal synthetic audio wave: 1 channel, 2 bytes/sample, 44100Hz
        num_samples = max(44100, total_bits + 100)
        # 440Hz sine wave samples
        samples = [int(1000 * (i % 50)) for i in range(num_samples)]
        for i in range(total_bits):
            samples[i] = (samples[i] & ~1) | data_bits[i]

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(44100)
            raw_frames = struct.pack(f"<{num_samples}h", *samples)
            wf.writeframes(raw_frames)
        return buf.getvalue()

    def extract(self, carrier_bytes: bytes, key: bytes) -> bytes:
        buf = io.BytesIO(carrier_bytes)
        with wave.open(buf, "rb") as wf:
            num_frames = wf.getnframes()
            raw_frames = wf.readframes(num_frames)

        samples = struct.unpack(f"<{num_frames}h", raw_frames)
        bits = [s & 1 for s in samples]

        def bits_to_bytes(bit_list: list[int]) -> bytes:
            out = bytearray()
            for i in range(0, len(bit_list) - 7, 8):
                byte = 0
                for bit in bit_list[i:i+8]:
                    byte = (byte << 1) | bit
                out.append(byte)
            return bytes(out)

        if len(bits) < 32:
            return b""
        header = bits_to_bytes(bits[:32])
        (payload_len,) = struct.unpack(">I", header)

        total_payload_bits = payload_len * 8
        if len(bits) < 32 + total_payload_bits:
            return b""

        payload_bits = bits[32 : 32 + total_payload_bits]
        return bits_to_bytes(payload_bits)

register(WavLsbCarrier)
