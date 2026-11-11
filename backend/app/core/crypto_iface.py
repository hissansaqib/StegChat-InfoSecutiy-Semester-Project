"""Interface for cryptographic operations used by StegChat.

The concrete implementation lives in ``backend/app/core/crypto_service.py``.
"""

from typing import Any, Dict

class CryptoIface:
    """Abstract base class defining required crypto methods.
    
    Implementations must provide encryption/decryption for at‑rest and lab data.
    """

    # At‑rest
    def encrypt_at_rest(self, plaintext: bytes, aad: bytes = b"") -> Dict[str, str]:
        raise NotImplementedError

    def decrypt_at_rest(self, payload: Dict[str, Any]) -> bytes:
        raise NotImplementedError

    # Lab‑specific
    def encrypt_lab(self, plaintext: bytes, aad: bytes = b"") -> Dict[str, str]:
        raise NotImplementedError

    def decrypt_lab(self, payload: Dict[str, Any]) -> bytes:
        raise NotImplementedError

