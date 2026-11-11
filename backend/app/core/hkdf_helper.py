*** Begin File: backend/app/core/hkdf_helper.py ***
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

def hkdf_derive(master_key: bytes, info: str, length: int = 32) -> bytes:
    """Derive `length` bytes using HKDF‑SHA256 with the given `info` string."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=None,
        info=info.encode(),
        backend=default_backend(),
    )
    return hkdf.derive(master_key)
*** End File ***
