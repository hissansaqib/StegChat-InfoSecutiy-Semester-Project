# backend/app/core/at_rest_cipher.py
"""AtRestCipher implements AES-256-GCM encryption/decryption for data at rest.
It uses the master key from the environment variable ``STEGCHAT_MASTER_KEY`` (base64-encoded 32-byte key).
The nonce is a random 12-byte (96-bit) value per encryption.
AAD can be supplied by caller and is included in the payload for integrity verification.
"""

import base64
import os
from typing import Dict, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class AtRestCipher:
    """AES‑256‑GCM cipher for at‑rest encryption.
    
    Provides ``encrypt`` and ``decrypt`` methods returning/accepting base64‑encoded payloads.
    """

    def __init__(self) -> None:
        master_key_b64 = os.getenv("STEGCHAT_MASTER_KEY")
        if not master_key_b64:
            raise RuntimeError("STEGCHAT_MASTER_KEY not set in environment")
        try:
            key = base64.b64decode(master_key_b64)
        except Exception as exc:
            raise RuntimeError("STEGCHAT_MASTER_KEY must be valid base64") from exc
        if len(key) != 32:
            raise RuntimeError("STEGCHAT_MASTER_KEY must decode to 32 bytes (256‑bit)")
        self._key = key
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: bytes, aad: bytes = b"") -> Dict[str, str]:
        """Encrypt ``plaintext`` with optional ``aad``.

        Returns a dict with base64‑encoded ``nonce``, ``ciphertext`` and ``aad``.
        """
        nonce = os.urandom(12)  # 96‑bit nonce for AES‑GCM
        ct = self._aesgcm.encrypt(nonce, plaintext, aad)
        return {
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ct).decode("ascii"),
            "aad": base64.b64encode(aad).decode("ascii"),
        }

    def decrypt(self, payload: Dict[str, Any]) -> bytes:
        """Decrypt a payload produced by :meth:`encrypt`.

        ``payload`` must contain ``nonce`` and ``ciphertext`` (base64 strings) and optionally ``aad``.
        Raises ``cryptography.exceptions.InvalidTag`` on authentication failure.
        """
        nonce = base64.b64decode(payload["nonce"])
        ct = base64.b64decode(payload["ciphertext"])
        aad_b64 = payload.get("aad", "")
        aad = base64.b64decode(aad_b64) if aad_b64 else b""
        return self._aesgcm.decrypt(nonce, ct, aad)

