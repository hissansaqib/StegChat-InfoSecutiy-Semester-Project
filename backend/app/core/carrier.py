"""Carrier contract definitions.

Each carrier module must expose a class implementing the ``Carrier`` interface.
The interface defines two core operations:

* ``embed(payload: bytes, key: bytes) -> bytes`` – embed a payload into a carrier
  and return the carrier bytes.
* ``extract(carrier_bytes: bytes, key: bytes) -> bytes`` – recover the original
  payload from carrier bytes.

The ``metadata`` property provides a human‑readable description used by the
registry and API documentation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Carrier(ABC):
    """Abstract base class for all steganography carriers.

    Implementations may be simple placeholders (as in ``fake_carrier``) or
    full steganographic algorithms later added by team members.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for the carrier (e.g., ``"png_lsb"``)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human friendly name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the carrier's technique."""

    @abstractmethod
    def embed(self, payload: bytes, key: bytes) -> bytes:
        """Embed ``payload`` into a carrier using ``key``.

        Returns the carrier bytes ready for transmission or storage.
        """

    @abstractmethod
    def extract(self, carrier_bytes: bytes, key: bytes) -> bytes:
        """Extract the original payload from ``carrier_bytes`` using ``key``.
        """

