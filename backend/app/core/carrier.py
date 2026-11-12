"""Carrier contract definitions and typed exceptions.

Single unified contract used by every carrier and feature:
- info: CarrierInfo metadata
- validate(data) -> bool
- capacity(data, options=None) -> int (in payload bytes)
- embed(cover, payload, params) -> bytes
- extract(stego, params) -> bytes
- measure(cover, stego) -> dict
- features(data) -> dict
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Typed Domain Exceptions
# ---------------------------------------------------------------------------

class CarrierError(Exception):
    """Base error for all carrier operations."""
    pass

class CapacityExceeded(CarrierError):
    """Raised when payload exceeds carrier capacity."""
    def __init__(self, message: str = "Payload exceeds carrier capacity", available: int = 0, required: int = 0):
        super().__init__(message)
        self.available = available
        self.required = required

class UnsupportedFormat(CarrierError):
    """Raised when data format or mime type is unsupported or corrupted header."""
    pass

class CorruptCarrier(CarrierError):
    """Raised when carrier structure is malformed or damaged."""
    pass

class ExtractionFailed(CarrierError):
    """Raised when payload extraction fails due to wrong seed or missing data."""
    pass

# ---------------------------------------------------------------------------
# Schemas & Metadata Models
# ---------------------------------------------------------------------------

class CarrierKind(str, Enum):
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    TEXT = "TEXT"

class CarrierInfo(BaseModel):
    id: str
    kind: CarrierKind
    display_name: str
    accepted_mime: List[str]
    output_mime: str
    deliverable: bool = True
    modes_schema: Dict[str, Any] = Field(default_factory=dict)
    limitations: List[str] = Field(default_factory=list)
    version: str = "1.0.0"

class EmbedParams(BaseModel):
    seed: Optional[str | bytes] = None
    options: Dict[str, Any] = Field(default_factory=dict)

class ExtractParams(BaseModel):
    seed: Optional[str | bytes] = None
    options: Dict[str, Any] = Field(default_factory=dict)

# ---------------------------------------------------------------------------
# Base Carrier Interface
# ---------------------------------------------------------------------------

class Carrier(ABC):
    """Abstract single contract for all steganographic carriers."""

    @property
    @abstractmethod
    def info(self) -> CarrierInfo:
        """Return full carrier metadata, capabilities, schema, and limitations."""
        ...

    @abstractmethod
    def validate(self, data: bytes) -> bool:
        """Validate if raw data conforms to the expected carrier format."""
        ...

    @abstractmethod
    def capacity(self, data: bytes, options: Optional[Dict[str, Any]] = None) -> int:
        """Calculate maximum raw payload bytes that can be embedded into data.
        
        Must account for shared frame overhead (8 bytes).
        Returns 0 if carrier cannot hold even the 8-byte frame header.
        """
        ...

    @abstractmethod
    def embed(self, cover: bytes, payload: bytes, params: Optional[Dict[str, Any] | EmbedParams] = None) -> bytes:
        """Embed payload into cover medium using shared frame and params.
        
        params:
          seed: 32-byte (or string) pseudo-random generator key
          options: carrier-specific options
        Raises:
          CapacityExceeded: if payload > capacity
          UnsupportedFormat: if cover format invalid
        """
        ...

    @abstractmethod
    def extract(self, stego: bytes, params: Optional[Dict[str, Any] | ExtractParams] = None) -> bytes:
        """Extract hidden payload from stego medium using params (seed, options).
        
        Raises:
          ExtractionFailed: if seed is wrong, CRC fails, or carrier data corrupt
          UnsupportedFormat: if stego format invalid
          CorruptCarrier: if container damaged
        """
        ...

    @abstractmethod
    def measure(self, cover: bytes, stego: bytes) -> Dict[str, Any]:
        """Compute fidelity and distortion metrics between cover and stego medium.
        
        E.g., PSNR, SSIM, MSE for image; SNR for audio; character diff for text.
        """
        ...

    @abstractmethod
    def features(self, data: bytes) -> Dict[str, Any]:
        """Extract domain features for steganalysis (e.g. LSB distribution, frequency)."""
        ...
