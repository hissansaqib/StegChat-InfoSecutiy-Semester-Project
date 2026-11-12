"""Carrier package registry.

One line per carrier registration using the unified Carrier contract.
"""

from typing import Dict, List, Type
from ..core.carrier import Carrier, CarrierInfo

registry: Dict[str, Carrier] = {}

def register(carrier_cls: Type[Carrier]) -> None:
    """Register an instantiated carrier singleton into the global registry."""
    instance = carrier_cls()
    registry[instance.info.id] = instance

def get_carrier(carrier_id: str) -> Carrier:
    """Retrieve an instantiated carrier by ID or raise KeyError."""
    if carrier_id not in registry:
        raise KeyError(f"Carrier '{carrier_id}' not found")
    return registry[carrier_id]

def list_carriers() -> List[str]:
    """Return all registered carrier IDs."""
    return list(registry.keys())

def get_all_carrier_info() -> List[CarrierInfo]:
    """Return metadata and capabilities for all registered carriers."""
    return [c.info for c in registry.values()]

# ---------------------------------------------------------------------------
# One line per carrier registration
# ---------------------------------------------------------------------------
from .fake_carrier import FakeCarrier; register(FakeCarrier)
from .png_lsb import PngLsbCarrier; register(PngLsbCarrier)
from .wav_lsb import WavLsbCarrier; register(WavLsbCarrier)
from .text_zw import TextZwCarrier; register(TextZwCarrier)
