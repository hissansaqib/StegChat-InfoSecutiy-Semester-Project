"""Core schemas for the API.

Defines request/response models for carrier operations and other endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

class CarrierPayload(BaseModel):
    """Payload to embed or extract using a carrier.

    ``payload``: base64‑encoded bytes of the data to embed.
    ``key``: base64‑encoded secret key used by the carrier.
    """

    payload: str = Field(..., description="Base64‑encoded payload bytes")
    key: str = Field(..., description="Base64‑encoded key bytes")

class CarrierResult(BaseModel):
    """Result returned by carrier operations.

    ``carrier_bytes``: base64‑encoded carrier bytes containing the payload.
    """

    carrier_bytes: str = Field(..., description="Base64‑encoded carrier bytes")

