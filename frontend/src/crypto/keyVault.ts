// src/crypto/keyVault.ts
// Core cryptographic primitives for StegChat client‑side encryption.

// Web Crypto API (available via window.crypto.subtle in browsers)
const subtle = window.crypto.subtle;

import { sha256 } from "@noble/hashes/sha256";
import { hkdf } from "@noble/hashes/hkdf";
import { argon2id } from "@noble/hashes/argon2"; // only used in the worker (kept for type safety)

export type KdfId = "argon2id" | "pbkdf2";
export interface Argon2Params {
  m: number; // memory in KiB
  t: number; // iterations
  p: number; // parallelism
}
export interface Pbkdf2Params {
  iterations: number; // >= 600_000
}
export interface KdfInfo {
  id: KdfId;
  params: Argon2Params | Pbkdf2Params;
}

/** Derive a 256‑bit master key from a passphrase. */
export async function deriveMasterKey(
  passphrase: string,
  salt: Uint8Array,
  kdf: KdfInfo,
): Promise<CryptoKey> {
  const enc = new TextEncoder();
  const pwdBytes = enc.encode(passphrase);

  if (kdf.id === "argon2id") {
    // Run Argon2id in a WebWorker to avoid blocking UI.
    const worker = new Worker(new URL("./argon2Worker.ts", import.meta.url), { type: "module" });
    const derived: Uint8Array = await new Promise((resolve, reject) => {
      worker.onmessage = (e) => resolve(new Uint8Array(e.data as ArrayBuffer));
      worker.onerror = reject;
      worker.postMessage({ pwd: pwdBytes, salt, params: kdf.params as Argon2Params });
    });
    worker.terminate();
    return await subtle.importKey("raw", derived, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
  }

  // PBKDF2‑SHA256 (native WebCrypto)
  const baseKey = await subtle.importKey(
    "raw",
    pwdBytes,
    { name: "PBKDF2" },
    false,
    ["deriveKey"],
  );
  const pbkdf2Info = kdf.params as Pbkdf2Params;
  return await subtle.deriveKey(
    {
      name: "PBKDF2",
      hash: "SHA-256",
      salt,
      iterations: pbkdf2Info.iterations,
    },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

/** Generate an ECDH P‑256 key pair. */
export async function generateECDHKeyPair(): Promise<CryptoKeyPair> {
  return await subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveKey", "deriveBits"],
  );
}

/** Wrap a private key with the master key (AES‑GCM). */
export async function wrapPrivateKey(
  privateKey: CryptoKey,
  masterKey: CryptoKey,
): Promise<{ wrapped: Uint8Array; nonce: Uint8Array }> {
  const exported = await subtle.exportKey("pkcs8", privateKey);
  const nonce = crypto.getRandomValues(new Uint8Array(12)); // 96‑bit nonce for AES‑GCM
  const ciphertext = await subtle.encrypt({ name: "AES-GCM", iv: nonce }, masterKey, exported);
  return { wrapped: new Uint8Array(ciphertext), nonce };
}

/** Unwrap a private key using the master key. */
export async function unwrapPrivateKey(
  wrapped: Uint8Array,
  nonce: Uint8Array,
  masterKey: CryptoKey,
): Promise<CryptoKey> {
  const decrypted = await subtle.decrypt({ name: "AES-GCM", iv: nonce }, masterKey, wrapped);
  return await subtle.importKey(
    "pkcs8",
    decrypted,
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveKey", "deriveBits"],
  );
}

/** Derive a per‑conversation AEAD key from ECDH + HKDF‑SHA256. */
export async function deriveConversationKey(
  localPriv: CryptoKey,
  peerPublicJwk: JsonWebKey,
  conversationId: string,
  alg: "aes-256-gcm" | "chacha20-poly1305",
): Promise<CryptoKey> {
  const peerPub = await subtle.importKey(
    "jwk",
    peerPublicJwk,
    { name: "ECDH", namedCurve: "P-256" },
    false,
    [],
  );
  const shared = await subtle.deriveBits({ name: "ECDH", public: peerPub }, localPriv, 256);
  const info = new TextEncoder().encode(`stegchat/msg/v1|${conversationId}`);
  const keyBytes = hkdf(sha256, new Uint8Array(shared), new Uint8Array(32).fill(0), info, 32);
  const algorithm = alg === "aes-256-gcm" ? { name: "AES-GCM", length: 256 } : { name: "ChaCha20-Poly1305", length: 256 } as any;
  return await subtle.importKey("raw", keyBytes, algorithm, false, ["encrypt", "decrypt"]);
}

/** Derive the carrier seed for the Lab endpoint. */
export async function deriveCarrierSeed(
  localPriv: CryptoKey,
  peerPublicJwk: JsonWebKey,
  conversationId: string,
): Promise<Uint8Array> {
  const peerPub = await subtle.importKey(
    "jwk",
    peerPublicJwk,
    { name: "ECDH", namedCurve: "P-256" },
    false,
    [],
  );
  const shared = await subtle.deriveBits({ name: "ECDH", public: peerPub }, localPriv, 256);
  const info = new TextEncoder().encode(`stegchat/seed/v1|${conversationId}`);
  return hkdf(sha256, new Uint8Array(shared), new Uint8Array(32).fill(0), info, 32);
}

/** Compute fingerprint (safety number) from an array of JWKs. */
export function computeFingerprint(publicJwks: JsonWebKey[]): string {
  const sorted = publicJwks.slice().sort((a, b) => (a.kid ?? "").localeCompare(b.kid ?? ""));
  const concatenated = sorted.map((j) => JSON.stringify(j)).join("");
  const hash = sha256(new TextEncoder().encode(concatenated));
  // Four groups of 4 hex chars (16 chars total).
  return Array.from({ length: 4 }, (_, i) =>
    Buffer.from(hash.slice(i * 8, (i + 1) * 8)).toString("hex").toUpperCase(),
  ).join(" ");
}

/** API helpers – thin wrappers around the existing api client. */
import { api } from "../api/client";
export const uploadKeyBundle = async (bundle: any) => {
  // The backend expects a POST to /keys/bundle (not yet existent in the client).
  // We'll use a generic fetch here to avoid typing issues.
  const res = await fetch(`/api/v1/keys/bundle`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bundle),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Failed to upload key bundle");
  }
  return await res.json();
};
export const fetchMyPublicKey = async () => {
  // Re‑use the /crypto/settings endpoint which already returns the public JWK list.
  const data = await api.getCryptoSettings();
  return data;
};

