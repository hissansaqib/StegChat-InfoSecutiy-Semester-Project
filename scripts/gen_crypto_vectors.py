"""Utility to generate test vectors for the crypto subsystem.

It uses a deterministic master key (base64) and encrypts a few fixed plaintext/AAD pairs
with the AtRestCipher, writing the resulting payloads to ``docs/crypto-vectors.json``.
"""
import os, json, base64
import os, sys, json, base64
sys.path.append(os.path.abspath('backend'))
from app.core.at_rest_cipher import AtRestCipher

def main():
    # Use a fixed master key for reproducibility
    master_key = base64.b64encode(b'\x01' * 32).decode('ascii')
    os.environ['STEGCHAT_MASTER_KEY'] = master_key
    cipher = AtRestCipher()
    vectors = []
    samples = [
        {"plaintext": b"hello world", "aad": b"test-aad-1"},
        {"plaintext": b"\x00\x01\x02", "aad": b""},
        {"plaintext": b"The quick brown fox jumps over the lazy dog", "aad": b"metadata"},
    ]
    for i, s in enumerate(samples):
        payload = cipher.encrypt(s["plaintext"], s["aad"])
        vectors.append({
            "id": i,
            "plaintext": base64.b64encode(s["plaintext"]).decode('ascii'),
            "aad": base64.b64encode(s["aad"]).decode('ascii'),
            "payload": payload,
        })
    with open('docs/crypto-vectors.json', 'w') as f:
        json.dump(vectors, f, indent=2)
    print('Generated', len(vectors), 'vectors to docs/crypto-vectors.json')

if __name__ == '__main__':
    main()
