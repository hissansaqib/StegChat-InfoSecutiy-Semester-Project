"""Carrier package initialization.

Exports:
- ``registry`` – dict mapping carrier IDs to carrier classes.
- ``register(carrier_cls)`` – register a carrier class.
- ``get_carrier(id)`` – retrieve a carrier class or raise KeyError.
- ``list_carriers()`` – return a list of available carrier IDs.
"""

from typing import Dict, List, Type
from ..core.carrier import Carrier

registry: Dict[str, Type[Carrier]] = {}

def register(carrier_cls: Type[Carrier]) -> None:
    carrier_instance = carrier_cls()
    carrier_id = carrier_instance.id
    registry[carrier_id] = carrier_cls

def get_carrier(carrier_id: str) -> Type[Carrier]:
    if carrier_id not in registry:
        raise KeyError(f"Carrier '{carrier_id}' not found")
    return registry[carrier_id]

def list_carriers() -> List[str]:
    return list(registry.keys())

# Register built-in carriers
from .fake_carrier import FakeCarrier
from .png_lsb import PngLsbCarrier
from .wav_lsb import WavLsbCarrier

register(FakeCarrier)
register(PngLsbCarrier)
register(WavLsbCarrier)
