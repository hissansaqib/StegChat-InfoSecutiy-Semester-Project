"""Utility to generate test vectors for the crypto subsystem.

Encrypts fixed plaintext/AAD pairs using AtRestCipher and LabCipher,
writing the resulting envelopes and vectors to ``docs/crypto-vectors.json``.
"""
import os, sys, json, base64

sys.path.append(os.path.abspath('backend'))
from app.crypto import AtRestCipher, LabCipher, SUPPORTED_ALGORITHMS

def main():
    # Use a fixed master key for reproducibility
    master_key = base64.b64encode(b'\x01' * 32).decode('ascii')
    os.environ['STEGCHAT_MASTER_KEY'] = master_key
    cipher = AtRestCipher()
    lab_cipher = LabCipher(ikm=b"known-ikm-seed-for-vectors-1234")

    vectors = []
    samples = [
        {"plaintext": b"hello world", "aad": b"test-aad-1"},
        {"plaintext": b"\x00\x01\x02", "aad": b""},
        {"plaintext": b"The quick brown fox jumps over the lazy dog", "aad": b"metadata"},
    ]

    for alg in ["aes-256-gcm", "chacha20-poly1305"]:
        for i, s in enumerate(samples):
            envelope = cipher.encrypt(s["plaintext"], alg=alg, aad=s["aad"])
            vectors.append({
                "cipher_service": "AtRestCipher",
                "alg": alg,
                "sample_id": i,
                "plaintext_b64": base64.b64encode(s["plaintext"]).decode('ascii'),
                "aad_b64": base64.b64encode(s["aad"]).decode('ascii'),
                "envelope": envelope.dict(),
            })

    os.makedirs('docs', exist_ok=True)
    with open('docs/crypto-vectors.json', 'w') as f:
        json.dump(vectors, f, indent=2)
    print('Generated', len(vectors), 'vectors to docs/crypto-vectors.json')

if __name__ == '__main__':
    main()
