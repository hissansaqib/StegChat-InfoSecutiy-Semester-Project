"""Shared frame & position generator for steganographic carriers.

Frame format:
- 4-byte whitened length: struct.pack(">I", len(payload)) ^ keystream[:4]
- N-byte whitened payload: payload[i] ^ keystream[4 + i]
- 4-byte whitened CRC32: struct.pack(">I", zlib.crc32(payload)) ^ keystream[4 + N : 8 + N]

Keystream & positions:
- Uses numpy.random.Generator with PCG64 initialized from a 32-byte seed.
- If seed is shorter or longer, HKDF or SHA256 expands/hashes it to 32 bytes.
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from typing import List, Sequence
import numpy as np

FRAME_OVERHEAD = 8  # 4 bytes length + 4 bytes CRC32

def normalize_seed(seed: bytes | str | None) -> bytes:
    """Normalize arbitrary seed input into 32-byte raw seed."""
    if seed is None:
        seed = b"default_stegchat_32_byte_seed_pad!"
    elif isinstance(seed, str):
        seed = seed.encode("utf-8")
    if len(seed) == 32:
        return seed
    return hashlib.sha256(seed).digest()

def get_pcg64_generator(seed: bytes | str | None) -> np.random.Generator:
    """Return a numpy Generator powered by PCG64 with seed sequence from 32-byte seed."""
    raw_seed = normalize_seed(seed)
    # Convert 32 bytes into array of four 64-bit uints for SeedSequence
    words = struct.unpack(">4Q", raw_seed)
    seq = np.random.SeedSequence(words)
    return np.random.Generator(np.random.PCG64(seq))

def generate_keystream(seed: bytes | str | None, length: int) -> bytes:
    """Generate deterministic pseudorandom keystream of specified length."""
    if length <= 0:
        return b""
    rng = get_pcg64_generator(seed)
    # Generate uint8 bytes
    return rng.bytes(length)

def generate_positions(seed: bytes | str | None, total_slots: int, count: int) -> List[int]:
    """Generate pseudo-random distinct slot indices using PCG64."""
    if count > total_slots:
        raise ValueError(f"Requested {count} slots, but only {total_slots} available.")
    rng = get_pcg64_generator(seed)
    # Permutation or choice
    indices = rng.permutation(total_slots)[:count]
    return indices.tolist()

def build_frame(payload: bytes, seed: bytes | str | None) -> bytes:
    """Construct whitened frame: [whitened_length(4)] + [whitened_payload(N)] + [whitened_crc(4)]."""
    n = len(payload)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    keystream = generate_keystream(seed, n + 8)

    # 1. Whitened length
    raw_len = struct.pack(">I", n)
    whitened_len = bytes(b ^ k for b, k in zip(raw_len, keystream[:4]))

    # 2. Whitened payload
    whitened_payload = bytes(b ^ k for b, k in zip(payload, keystream[4: 4 + n]))

    # 3. Whitened CRC32
    raw_crc = struct.pack(">I", crc)
    whitened_crc = bytes(b ^ k for b, k in zip(raw_crc, keystream[4 + n: 8 + n]))

    return whitened_len + whitened_payload + whitened_crc

def read_frame_length(raw_4_bytes: bytes, seed: bytes | str | None) -> int:
    """Unwhiten the 4-byte header and return the claimed payload length."""
    if len(raw_4_bytes) < 4:
        raise ValueError("Header must be at least 4 bytes")
    keystream = generate_keystream(seed, 4)
    unwhitened_len = bytes(b ^ k for b, k in zip(raw_4_bytes, keystream[:4]))
    (payload_len,) = struct.unpack(">I", unwhitened_len)
    return payload_len

def parse_frame(frame_bytes: bytes, seed: bytes | str | None) -> bytes:
    """Parse, unwhiten and verify CRC32 from frame bytes.
    
    Returns original payload.
    Raises ValueError on CRC mismatch or corrupt/truncated data.
    """
    if len(frame_bytes) < 8:
        raise ValueError("Frame truncated: smaller than 8 bytes overhead")

    payload_len = read_frame_length(frame_bytes[:4], seed)
    expected_frame_len = payload_len + 8
    if len(frame_bytes) < expected_frame_len:
        raise ValueError(
            f"Frame incomplete: header indicates {payload_len} bytes payload (total {expected_frame_len}), but got {len(frame_bytes)}"
        )

    keystream = generate_keystream(seed, payload_len + 8)

    whitened_payload = frame_bytes[4: 4 + payload_len]
    payload = bytes(b ^ k for b, k in zip(whitened_payload, keystream[4: 4 + payload_len]))

    whitened_crc = frame_bytes[4 + payload_len: 8 + payload_len]
    raw_crc = bytes(b ^ k for b, k in zip(whitened_crc, keystream[4 + payload_len: 8 + payload_len]))
    (expected_crc,) = struct.unpack(">I", raw_crc)

    actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if actual_crc != expected_crc:
        raise ValueError(f"CRC32 mismatch (expected {expected_crc:#x}, computed {actual_crc:#x}). Invalid seed or corrupted carrier.")

    return payload
