// src/crypto/argon2Worker.ts
// Web Worker that performs Argon2id key derivation using @noble/hashes.

import { argon2id } from "@noble/hashes/argon2";

self.onmessage = (e: MessageEvent) => {
  const { pwd, salt, params } = e.data as {
    pwd: Uint8Array;
    salt: Uint8Array;
    params: { m: number; t: number; p: number };
  };
  const { m, t, p } = params;
  // Derive a 32‑byte key (256 bits).
  const derived = argon2id(pwd, salt, { m, t, p, dkLen: 32 });
  // Transfer the raw buffer back to the main thread.
  (self as any).postMessage(derived.buffer, [derived.buffer]);
};

