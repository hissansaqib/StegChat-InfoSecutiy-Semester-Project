"""Carrier package initialization.

Exports:
- ``registry`` – a dict mapping carrier IDs to carrier classes.
- ``get_carrier(id)`` – retrieve a carrier class or raise ``KeyError``.
- ``list_carriers()`` – return a list of available carrier IDs.

Each carrier module must import its class and register it by adding a single
line to the ``registry`` dict below. This keeps the registration side‑effects
local to the module and ensures automatic discovery.
"""

from typing import Dict, List, Type

from .carrier import Carrier

# Registry mapping carrier ID to the carrier class.
registry: Dict[str, Type[Carrier]] = {}

def register(carrier_cls: Type[Carrier]) -> None:
    """Register a ``Carrier`` subclass.

    The subclass must define a unique ``id`` property. Registration is a
    side‑effect performed by the carrier module on import.
    """

    carrier_id = carrier_cls().id
    if carrier_id in registry:
        raise ValueError(f"Carrier ID '{carrier_id}' already registered")
    registry[carrier_id] = carrier_cls

def get_carrier(carrier_id: str) -> Type[Carrier]:
    """Return the carrier class for ``carrier_id``.

    Raises ``KeyError`` if the carrier is unknown.
    """
    return registry[carrier_id]

def list_carriers() -> List[str]:
    """Return a list of all registered carrier IDs."""
    return list(registry.keys())
