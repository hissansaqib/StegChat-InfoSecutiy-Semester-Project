"""Fake carrier implementation used as a working reference.

This carrier does **not** provide real steganography – it simply XOR‑whitens
the payload with a key and returns the result as the carrier bytes. It is
intended for testing and as a template for real implementations.
"""

from __future__ import annotations

from typing import Any

from ..carrier import Carrier
from .. import register

class FakeCarrier(Carrier):
    """Trivial XOR‑based carrier.

    * ``id``: ``"fake"``
    * ``name``: ``"Fake Carrier"``
    * ``description``: short placeholder description.
    """

    @property
    def id(self) -> str:
        return "fake"

    @property
    def name(self) -> str:
        return "Fake Carrier"

    @property
    def description(self) -> str:
        return "A trivial XOR‑based carrier used for testing purposes. Not real steganography."

    def embed(self, payload: bytes, key: bytes) -> bytes:
        # Simple XOR of payload with repeating key.
        if not key:
            raise ValueError("Key must be non‑empty for fake carrier")
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(payload))

    def extract(self, carrier_bytes: bytes, key: bytes) -> bytes:
        # XOR is symmetric – same operation recovers payload.
        if not key:
            raise ValueError("Key must be non‑empty for fake carrier")
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(carrier_bytes))

# Register this carrier on import.
register(FakeCarrier)

