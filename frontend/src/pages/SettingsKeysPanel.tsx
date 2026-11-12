// src/pages/SettingsKeysPanel.tsx
import React, { useContext, useEffect, useState } from "react";
import { api } from "../api/client";
import { CryptoContext } from "../contexts/CryptoContext";

export const SettingsKeysPanel: React.FC = () => {
  const { masterKey, ecdhKeyPair, locked, unlock } = useContext(CryptoContext);
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [rotating, setRotating] = useState(false);

  useEffect(() => {
    api.getCryptoSettings()
      .then(setSettings)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleRotate = async () => {
    if (!masterKey || !ecdhKeyPair) return;
    setRotating(true);
    try {
      // Generate fresh vault (new salt, new ECDH key pair)
      const newSalt = crypto.getRandomValues(new Uint8Array(16));
      const newKdf = { id: "argon2id", params: { m: 65536, t: 3, p: 1 } } as any;
      const newMaster = await deriveMasterKey("placeholder", newSalt, newKdf); // passphrase will be re‑entered by user in real flow
      const newPair = await generateECDHKeyPair();
      const { wrapped, nonce } = await wrapPrivateKey(newPair.privateKey, newMaster);
      const publicJwk = await crypto.subtle.exportKey("jwk", newPair.publicKey);
      const fingerprint = computeFingerprint([publicJwk as any]);
      const bundle = {
        public_jwk: publicJwk,
        wrapped_private: btoa(String.fromCharCode(...wrapped)),
        wrapped_nonce: btoa(String.fromCharCode(...nonce)),
        salt: btoa(String.fromCharCode(...newSalt)),
        kdf: newKdf,
        fingerprint,
        key_id: "master-v1",
      };
      await api.uploadKeyBundle(bundle);
      // Update context with new keys
      unlock(newMaster, newPair);
      alert("Vault rotated successfully");
    } catch (e) {
      console.error(e);
      alert("Failed to rotate vault");
    } finally {
      setRotating(false);
    }
  };

  if (loading) return <div className="text-xs text-slate-400">Loading key settings...</div>;

  return (
    <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl mb-4">
      <h3 className="text-sm font-bold text-white mb-2">Vault & Key Management</h3>
      <p className="text-xs text-slate-300 mb-2">
        Active Key Identifier: <span className="font-mono text-cyan-400">{settings?.active_key_id}</span>
      </p>
      <p className="text-xs text-slate-300 mb-2">
        Fingerprint (Safety Number): <span className="font-mono text-green-400">{settings?.fingerprint || "—"}</span>
      </p>
      <button
        onClick={handleRotate}
        disabled={rotating}
        className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-xs rounded disabled:opacity-50"
      >
        {rotating ? "Rotating…" : "Rotate Vault"}
      </button>
    </div>
  );
};

