# StegChat Cryptographic Architecture & Threat Protection Model

StegChat implements a strict two-tier defense-in-depth cryptographic model designed to protect confidentiality, integrity, and authenticity across transit and storage.

---

## 1. Cryptographic Primitive Layer (`backend/app/crypto`)

All low-level cryptographic operations are strictly isolated to `backend/app/crypto`. No other module in the codebase is permitted to import the underlying `cryptography` library.

### Supported AEAD Ciphers
Both ciphers operate as Authenticated Encryption with Associated Data (AEAD):
1. **AES-256-GCM** (NIST SP 800-38D): Hardware-accelerated Galois/Counter Mode with 256-bit keys, 96-bit nonces, and 128-bit authentication tags.
2. **ChaCha20-Poly1305** (RFC 8439): Stream cipher with Poly1305 MAC, resistant to cache-timing attacks without dedicated hardware acceleration.

### Cryptographic Envelope Schema
All ciphertexts are packaged inside a versioned envelope serialized to compact JSON or Base64:
```json
{
  "v": 1,
  "alg": "aes-256-gcm",
  "key_id": "master-v1",
  "nonce": "Base64(96-bit os.urandom)",
  "ciphertext": "Base64(ciphertext + 128-bit MAC tag)",
  "aad_hash": "Base64(SHA256(Associated Data))"
}
```

---

## 2. Multi-Tier Protection Model

StegChat structures data protection into two distinct security tiers:

| Property | Tier 1: At-Rest Database Storage | Tier 2: Steganographic / Lab Payloads |
| :--- | :--- | :--- |
| **Service** | `AtRestCipher` | `LabCipher` / End-to-End Key Agreement |
| **Key Origin** | Master Key (`STEGCHAT_MASTER_KEY` 256-bit) | Derived via HKDF-SHA256 (`stegchat/lab/v1`) |
| **Key Scope** | Server-wide; managed by platform operator | User-supplied passphrase or ephemeral session |
| **Tamper Binding** | Associated Data = `conversation_id` | Associated Data = `carrier_id` / metadata |
| **Server Visibility** | Server can decrypt messages to serve to members | Completely blind; server sees only stego carrier |

---

## 3. What Each Tier Protects and Does Not Protect

### Tier 1: At-Rest Cipher (`AtRestCipher`)

#### What It Protects:
* **Database Dump Compromise:** If an attacker steals the raw SQLite or PostgreSQL database file, backups, or volume snapshots, all message content remains unreadable ciphertext.
* **SQL Injection / Unauthenticated DB Querying:** Raw queries return opaque JSON envelopes without exposing message plaintexts.
* **Tampering & Forgery:** The 128-bit AEAD authentication tag guarantees that modifying a single bit of ciphertext or nonce causes immediate decryption refusal with zero plaintext leakage.
* **Cross-Conversation Swapping:** The `conversation_id` is cryptographically bound as Associated Data (AAD). A ciphertext copied from one conversation cannot be decrypted inside another conversation.

#### What It Does NOT Protect Against:
* **Fully Compromised Server Process:** An attacker with memory inspection or root access to the running backend process holding `STEGCHAT_MASTER_KEY` can decrypt Tier 1 records.
* **Malicious Server Operator:** The server operator can inspect Tier 1 messages because the server possesses the at-rest master key.

---

### Tier 2: Covert Steganographic Payload (`LabCipher` / End-to-End)

#### What It Protects:
* **Server Operator Surveillance:** Plaintext secret messages are encrypted using user-controlled passphrases before embedding into the cover container. The server operator cannot read the embedded secret without the passphrase.
* **Eavesdropping on Physical Network Transit:** Network sniffers inspect normal image (PNG), audio (WAV), or plain text traffic and see no obvious encryption headers due to PRNG position dispersion and zero-magic-byte frame whitening.
* **Deep Packet Inspection (DPI):** Traffic analysis observes valid image dimensions or audio samples rather than high-entropy cryptographic handshakes.

#### What It Does NOT Protect Against:
* **Compromised End-User Browser / Endpoint:** A compromised client machine with keyloggers or malware can capture input before encryption.
* **Statistical Steganalysis Anomalies:** If excessive payload is embedded relative to cover capacity, advanced $\chi^2$ or deep learning steganalysis may detect the presence of hidden modifications.

---

## 4. Key Rotation & Lifecycle

* **Key Identifiers (`key_id`):** Every envelope records the `key_id` that created it.
* **Backward Compatibility:** `AtRestCipher.register_historical_key(key_id, key_bytes)` allows older records to remain decryptable after active key rotation.
* **Production Safety:** In `APP_ENV=production`, the service refuses to boot if `STEGCHAT_MASTER_KEY` is omitted.

