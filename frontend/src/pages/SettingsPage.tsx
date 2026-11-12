import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCryptoSettings()
      .then(setSettings)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Security & Cryptography Architecture</h1>
        <p className="text-xs text-slate-400 mt-1">
          Inspection of authenticated AEAD ciphers, key rotation states, and multi-tier protection boundaries.
        </p>
      </div>

      {/* Key Status Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
              Active Key Identifier (Key Rotation Support)
            </span>
            <div className="text-lg font-mono font-bold text-indigo-400 mt-0.5">
              {settings?.active_key_id || 'master-v1'}
            </div>
          </div>
          <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 rounded-full text-xs font-bold font-mono">
            ACTIVE ENCRYPTION
          </span>
        </div>

        {/* Multi-Tier Protection Explanation */}
        <div className="mt-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Defense-in-Depth Protection Tiers
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-slate-800/60 border border-indigo-500/30 rounded-xl space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-base">🗄️</span>
                <span className="font-bold text-sm text-indigo-300">Tier 1: Server-Readable At-Rest</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {settings?.tier_info?.tier_1}
              </p>
              <div className="text-[11px] text-slate-400 font-mono bg-slate-950/60 p-2 rounded border border-slate-800">
                Guarantees raw database backups and stolen disk images contain only encrypted envelopes with zero plaintext leakage.
              </div>
            </div>

            <div className="p-4 bg-slate-800/60 border border-amber-500/30 rounded-xl space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-base">🕵️</span>
                <span className="font-bold text-sm text-amber-300">Tier 2: Browser/Lab Steganography</span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {settings?.tier_info?.tier_2}
              </p>
              <div className="text-[11px] text-slate-400 font-mono bg-slate-950/60 p-2 rounded border border-slate-800">
                The backend server and network monitors only ever observe synthetic or cover media with whitened, pseudorandom dispersed bits.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Algorithms Catalog */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4">
          Cryptographic Ciphers & Envelope Engine
        </h3>
        <div className="space-y-3">
          {settings?.algorithms?.map((alg: any) => (
            <div key={alg.id} className="p-4 bg-slate-800/50 border border-slate-700/80 rounded-xl space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">{alg.name}</span>
                  <span className="text-xs font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/50 px-2 py-0.5 rounded">
                    {alg.standard}
                  </span>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {alg.key_size_bytes * 8}-bit Key | {alg.nonce_size_bytes * 8}-bit Nonce
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">{alg.notes}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
