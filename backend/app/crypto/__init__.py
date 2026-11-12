"""StegChat Cryptographic Subsystem.

The ONLY place in the backend that touches cryptographic primitives (`cryptography` package).

Features:
- Ciphers: AES-256-GCM and ChaCha20-Poly1305, selectable by id.
- Versioned Envelope {v, alg, key_id, nonce, ciphertext, aad_hash}.
- 96-bit unique nonces via os.urandom.
- AtRestCipher service with key_id support, rotation support, auto-generated dev key in development,
  and refusal to start in production if STEGCHAT_MASTER_KEY is missing.
- LabCipher service derived using HKDF-SHA256 (info: b'stegchat/lab/v1').
- hkdf() helper function.
- Typed exceptions: UnknownAlgorithmError, UnsupportedVersionError, CryptoDecryptionError, CryptoConfigurationError.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

# ---------------------------------------------------------------------------
# Typed Domain Exceptions
# ---------------------------------------------------------------------------

class CryptoError(Exception):
    """Base error for crypto subsystem."""
    pass

class UnknownAlgorithmError(CryptoError):
    """Raised when an algorithm identifier is unrecognized."""
    pass

class UnsupportedVersionError(CryptoError):
    """Raised when an envelope schema version is unsupported."""
    pass

class CryptoDecryptionError(CryptoError):
    """Raised on authentication/MAC/tag failure, tampering, or wrong key."""
    pass

class CryptoConfigurationError(CryptoError):
    """Raised when master keys or environment configuration are invalid."""
    pass

# ---------------------------------------------------------------------------
# Supported Algorithms & Metadata
# ---------------------------------------------------------------------------

SUPPORTED_ALGORITHMS: Dict[str, Dict[str, Any]] = {
    "aes-256-gcm": {
        "id": "aes-256-gcm",
        "name": "AES-256-GCM",
        "key_size_bytes": 32,
        "nonce_size_bytes": 12,
        "tag_size_bytes": 16,
        "standard": "NIST SP 800-38D",
        "notes": "Hardware-accelerated (AES-NI) authenticated encryption with associated data.",
    },
    "chacha20-poly1305": {
        "id": "chacha20-poly1305",
        "name": "ChaCha20-Poly1305",
        "key_size_bytes": 32,
        "nonce_size_bytes": 12,
        "tag_size_bytes": 16,
        "standard": "RFC 8439",
        "notes": "Stream cipher with Poly1305 authenticator; constant-time without specialized hardware.",
    },
}

# ---------------------------------------------------------------------------
# Envelope Model & Serialization
# ---------------------------------------------------------------------------

class CryptoEnvelope(BaseModel):
    v: int = Field(default=1, description="Envelope format version")
    alg: str = Field(..., description="Cryptographic algorithm identifier")
    key_id: str = Field(default="default", description="Identifier of key used for rotation tracking")
    nonce: str = Field(..., description="Base64 encoded 96-bit nonce")
    ciphertext: str = Field(..., description="Base64 encoded ciphertext with trailing auth tag")
    aad_hash: str = Field(default="", description="Base64 encoded SHA-256 digest of Associated Data (AAD)")

    def to_compact_json(self) -> str:
        """Serialize envelope to compact single-line JSON."""
        return json.dumps(self.dict(), separators=(",", ":"))

    def to_base64(self) -> str:
        """Serialize envelope to compact URL-safe Base64 string."""
        return base64.urlsafe_b64encode(self.to_compact_json().encode("utf-8")).decode("ascii")

    @classmethod
    def from_string(cls, data: str | Dict[str, Any]) -> CryptoEnvelope:
        """Parse envelope from compact JSON string, Base64 string, or dictionary."""
        if isinstance(data, dict):
            return cls(**data)
        data = data.strip()
        if data.startswith("{") and data.endswith("}"):
            return cls(**json.loads(data))
        # Attempt Base64 decode
        try:
            raw_json = base64.urlsafe_b64decode(data).decode("utf-8")
            return cls(**json.loads(raw_json))
        except Exception as e:
            # Maybe raw standard Base64
            raw_json = base64.b64decode(data).decode("utf-8")
            return cls(**json.loads(raw_json))

# ---------------------------------------------------------------------------
# Primitive Keystream & Key Derivation (HKDF)
# ---------------------------------------------------------------------------

def hkdf(
    ikm: bytes,
    length: int = 32,
    salt: Optional[bytes] = None,
    info: bytes = b"stegchat/v1",
) -> bytes:
    """HKDF-SHA256 key derivation helper function."""
    hkdf_inst = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt or b"\x00" * 32,
        info=info,
    )
    return hkdf_inst.derive(ikm)

# ---------------------------------------------------------------------------
# Core Encryption & Decryption Functions
# ---------------------------------------------------------------------------

def compute_aad_hash(aad: bytes) -> str:
    """Return Base64 SHA-256 hash of AAD for tamper-evident binding."""
    if not aad:
        return ""
    digest = hashlib.sha256(aad).digest()
    return base64.b64encode(digest).decode("ascii")

def encrypt(
    plaintext: bytes,
    key: bytes,
    alg: str = "aes-256-gcm",
    aad: bytes = b"",
    key_id: str = "default",
) -> CryptoEnvelope:
    """Encrypt plaintext into a versioned CryptoEnvelope using specified AEAD cipher."""
    clean_alg = alg.lower().strip()
    if clean_alg not in SUPPORTED_ALGORITHMS:
        raise UnknownAlgorithmError(f"Unsupported cipher algorithm '{alg}'. Choose from {list(SUPPORTED_ALGORITHMS.keys())}")

    if len(key) != 32:
        raise CryptoConfigurationError(f"Encryption key must be exactly 32 bytes (got {len(key)})")

    # 96-bit (12 bytes) cryptographically secure random nonce
    nonce = os.urandom(12)

    if clean_alg == "aes-256-gcm":
        cipher = AESGCM(key)
    elif clean_alg == "chacha20-poly1305":
        cipher = ChaCha20Poly1305(key)
    else:
        raise UnknownAlgorithmError(clean_alg)

    ciphertext_and_tag = cipher.encrypt(nonce, plaintext, aad)

    return CryptoEnvelope(
        v=1,
        alg=clean_alg,
        key_id=key_id,
        nonce=base64.b64encode(nonce).decode("ascii"),
        ciphertext=base64.b64encode(ciphertext_and_tag).decode("ascii"),
        aad_hash=compute_aad_hash(aad),
    )

def decrypt(
    envelope: CryptoEnvelope | Dict[str, Any] | str,
    key_resolver: bytes | Dict[str, bytes],
    aad: bytes = b"",
) -> bytes:
    """Decrypt a CryptoEnvelope picking algorithm and key from envelope metadata.
    
    key_resolver: either raw 32-byte key, or a dict mapping key_id -> 32-byte key.
    """
    if not isinstance(envelope, CryptoEnvelope):
        envelope = CryptoEnvelope.from_string(envelope)

    if envelope.v != 1:
        raise UnsupportedVersionError(f"Envelope version v={envelope.v} is unsupported.")

    clean_alg = envelope.alg.lower().strip()
    if clean_alg not in SUPPORTED_ALGORITHMS:
        raise UnknownAlgorithmError(f"Unknown cipher algorithm '{envelope.alg}' in envelope.")

    # Verify AAD hash if present
    if envelope.aad_hash:
        expected_hash = compute_aad_hash(aad)
        if envelope.aad_hash != expected_hash:
            raise CryptoDecryptionError("AAD mismatch: Associated Data does not match envelope aad_hash.")

    # Resolve key by key_id if key_resolver is a key store dict
    if isinstance(key_resolver, dict):
        if envelope.key_id not in key_resolver:
            raise CryptoDecryptionError(f"Key ID '{envelope.key_id}' not found in active key store.")
        key = key_resolver[envelope.key_id]
    else:
        key = key_resolver

    if len(key) != 32:
        raise CryptoConfigurationError("Resolved key must be exactly 32 bytes.")

    try:
        nonce = base64.b64decode(envelope.nonce)
        ciphertext_and_tag = base64.b64decode(envelope.ciphertext)
    except Exception as e:
        raise CryptoDecryptionError(f"Malformed base64 envelope field: {e}") from e

    if len(nonce) != 12:
        raise CryptoDecryptionError(f"Nonce must be 12 bytes (got {len(nonce)})")

    if clean_alg == "aes-256-gcm":
        cipher = AESGCM(key)
    elif clean_alg == "chacha20-poly1305":
        cipher = ChaCha20Poly1305(key)
    else:
        raise UnknownAlgorithmError(clean_alg)

    try:
        plaintext = cipher.decrypt(nonce, ciphertext_and_tag, aad)
        return plaintext
    except InvalidTag as e:
        raise CryptoDecryptionError("Decryption failed: Authentication tag verification failed or wrong key/nonce.") from e
    except Exception as e:
        raise CryptoDecryptionError(f"Decryption failed: {e}") from e

# ---------------------------------------------------------------------------
# Services: AtRestCipher & LabCipher
# ---------------------------------------------------------------------------

class AtRestCipher:
    """Service for at-rest storage encryption of ordinary messages and sensitive records.
    
    Key management:
    - Reads master key from environment `STEGCHAT_MASTER_KEY` (base64 32 bytes).
    - If in production (`APP_ENV=production`) and missing, refuses to start.
    - If in development and missing, generates an ephemeral dev key with warning.
    - Supports key rotation: `register_historical_key(key_id, key_bytes)` keeps old keys readable.
    """

    def __init__(self, key_id: str = "master-v1") -> None:
        self.active_key_id = key_id
        self._key_store: Dict[str, bytes] = {}
        self._initialize_keys()

    def _initialize_keys(self) -> None:
        master_key_b64 = os.getenv("STEGCHAT_MASTER_KEY", "").strip()
        app_env = os.getenv("APP_ENV", "development").lower()

        if not master_key_b64:
            if app_env == "production":
                raise CryptoConfigurationError(
                    "FATAL: STEGCHAT_MASTER_KEY environment variable is required in production! Refusing to start."
                )
            # Development mode auto-generation
            dev_key = os.urandom(32)
            self._key_store[self.active_key_id] = dev_key
            print("[Crypto] WARNING: STEGCHAT_MASTER_KEY not set. Auto-generated ephemeral development key.")
            return

        try:
            key_bytes = base64.b64decode(master_key_b64)
        except Exception as exc:
            raise CryptoConfigurationError("STEGCHAT_MASTER_KEY must be valid Base64.") from exc

        if len(key_bytes) != 32:
            raise CryptoConfigurationError(f"STEGCHAT_MASTER_KEY must decode to 32 bytes (got {len(key_bytes)}).")

        self._key_store[self.active_key_id] = key_bytes

    def register_historical_key(self, key_id: str, key_bytes: bytes) -> None:
        """Register an older key to support decrypting legacy rotated envelopes."""
        if len(key_bytes) != 32:
            raise CryptoConfigurationError("Historical key must be 32 bytes.")
        self._key_store[key_id] = key_bytes

    def get_active_key(self) -> bytes:
        return self._key_store[self.active_key_id]

    def encrypt(
        self,
        plaintext: bytes,
        alg: str = "aes-256-gcm",
        aad: bytes = b"",
    ) -> CryptoEnvelope:
        return encrypt(
            plaintext=plaintext,
            key=self.get_active_key(),
            alg=alg,
            aad=aad,
            key_id=self.active_key_id,
        )

    def decrypt(self, envelope: CryptoEnvelope | Dict[str, Any] | str, aad: bytes = b"") -> bytes:
        return decrypt(envelope=envelope, key_resolver=self._key_store, aad=aad)

class LabCipher:
    """Service for experimental and lab-mode steganographic payload encryption.
    
    Keys are derived using HKDF-SHA256 with domain separation:
    - Info: b"stegchat/lab/v1"
    - Input Key Material (IKM) can be user-supplied passphrase, shared secret, or session key.
    """

    def __init__(self, ikm: bytes | str = b"stegchat-lab-default-secret-seed") -> None:
        if isinstance(ikm, str):
            ikm = ikm.encode("utf-8")
        self.derived_key = hkdf(ikm=ikm, length=32, salt=None, info=b"stegchat/lab/v1")
        self.key_id = "lab-hkdf-v1"

    def encrypt(
        self,
        plaintext: bytes,
        alg: str = "aes-256-gcm",
        aad: bytes = b"",
    ) -> CryptoEnvelope:
        return encrypt(
            plaintext=plaintext,
            key=self.derived_key,
            alg=alg,
            aad=aad,
            key_id=self.key_id,
        )

    def decrypt(self, envelope: CryptoEnvelope | Dict[str, Any] | str, aad: bytes = b"") -> bytes:
        return decrypt(envelope=envelope, key_resolver={self.key_id: self.derived_key}, aad=aad)

# Singleton instances for convenience
_default_at_rest: Optional[AtRestCipher] = None

def get_at_rest_cipher() -> AtRestCipher:
    global _default_at_rest
    if _default_at_rest is None:
        _default_at_rest = AtRestCipher()
    return _default_at_rest
