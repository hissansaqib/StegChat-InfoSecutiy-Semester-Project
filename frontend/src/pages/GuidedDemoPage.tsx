import React, { useState } from 'react';
import { api } from '../api/client';

export const GuidedDemoPage: React.FC = () => {
  const [carrierId, setCarrierId] = useState('png_lsb');
  const [algorithm, setAlgorithm] = useState('aes-256-gcm');
  const [secretMessage, setSecretMessage] = useState('Confidential Project Apollo Coordinates: 37.7749,-122.4194');
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);

  const handleRunDemo = async () => {
    setLoading(true);
    setCurrentStep(2);

    try {
      // Step 1 & 2: Embedding with selectable AEAD cipher
      const embedRes = await api.labEmbed({
        carrier_id: carrierId,
        message: secretMessage,
        algorithm: algorithm,
      });

      setCurrentStep(3);

      // Step 3: Extraction with cipher verification
      const extractRes = await api.labExtract({
        carrier_id: carrierId,
        carrier_bytes: embedRes.carrier_bytes,
      });

      setCurrentStep(4);

      // Step 4: Run Steganalysis
      const analysisRes = await api.runAnalysis({
        carrier_bytes: embedRes.carrier_bytes,
        carrier_id: carrierId,
      });

      setResults({
        embed: embedRes,
        extract: extractRes,
        analysis: analysisRes,
        success: extractRes.message === secretMessage,
      });
      setCurrentStep(5);
    } catch (err: any) {
      alert('Demo execution failed: ' + err.message);
      setCurrentStep(1);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Interactive Guided Demo</h1>
        <p className="text-sm text-slate-400 mt-1">
          Execute the end-to-end steganographic pipeline: Encode &rarr; Synthesize &rarr; Extract &rarr; Steganalysis.
        </p>
      </div>

      {/* Progress Stepper */}
      <div className="grid grid-cols-4 gap-2 text-center text-xs font-semibold">
        {[
          { step: 1, label: '1. Configure' },
          { step: 2, label: '2. Embed' },
          { step: 3, label: '3. Extract' },
          { step: 5, label: '4. Analysis' },
        ].map((s) => (
          <div
            key={s.step}
            className={`p-2.5 rounded-lg border transition ${
              currentStep >= s.step
                ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300 font-bold'
                : 'bg-slate-800 border-slate-700 text-slate-500'
            }`}
          >
            {s.label}
          </div>
        ))}
      </div>

      {/* Configuration Panel */}
      <div className="bg-slate-850 p-6 rounded-xl border border-slate-800 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Select Carrier Method
            </label>
            <select
              value={carrierId}
              disabled={loading}
              onChange={(e) => setCarrierId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="png_lsb">PNG Image LSB (Lossless 24-bit RGB)</option>
              <option value="wav_lsb">WAV Audio LSB (16-bit 44.1kHz PCM)</option>
              <option value="fake">Fake XOR Carrier (Baseline Test)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Cryptographic Cipher (AEAD)
            </label>
            <select
              value={algorithm}
              disabled={loading}
              onChange={(e) => setAlgorithm(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-indigo-500 font-mono text-xs"
            >
              <option value="aes-256-gcm">AES-256-GCM (Hardware Accelerated AEAD)</option>
              <option value="chacha20-poly1305">ChaCha20-Poly1305 (RFC 8439 Authenticated)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Secret Message
          </label>
          <textarea
            rows={3}
            disabled={loading}
            value={secretMessage}
            onChange={(e) => setSecretMessage(e.target.value)}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-indigo-500 font-mono text-sm"
          />
        </div>

        <button
          onClick={handleRunDemo}
          disabled={loading || !secretMessage.trim()}
          className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition disabled:opacity-50 shadow-lg flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              <span>Executing Pipeline...</span>
            </>
          ) : (
            'Run End-to-End Pipeline Demo'
          )}
        </button>
      </div>

      {/* Results Section */}
      {results && (
        <div className="bg-slate-850 p-6 rounded-xl border border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-700/60 pb-3">
            <h2 className="text-lg font-bold text-white">Pipeline Execution Report</h2>
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                results.success
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  : 'bg-red-500/20 text-red-400 border border-red-500/40'
              }`}
            >
              {results.success ? '✓ 100% Exact Recovery' : '✗ Extraction Discrepancy'}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
              <span className="text-xs text-slate-400 uppercase tracking-wider block">Embed Latency</span>
              <span className="text-2xl font-bold text-white mt-1 block">
                {results.embed.embed_time_ms} ms
              </span>
              <div className="flex items-center justify-between text-xs text-slate-500 mt-1">
                <span>{results.embed.carrier_size} B</span>
                {results.embed.stego_sha256 && (
                  <span className="px-1.5 py-0.5 rounded bg-slate-900 font-mono text-[10px] text-indigo-300 border border-slate-700" title={`Full SHA-256: ${results.embed.stego_sha256}`}>
                    SHA: {results.embed.stego_sha256.substring(0, 8)}…
                  </span>
                )}
              </div>
            </div>

            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
              <span className="text-xs text-slate-400 uppercase tracking-wider block">Extract Latency</span>
              <span className="text-2xl font-bold text-white mt-1 block">
                {results.extract.extract_time_ms} ms
              </span>
              <span className="text-xs text-slate-500">Payload: {results.extract.extracted_size} bytes</span>
            </div>

            <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
              <span className="text-xs text-slate-400 uppercase tracking-wider block">Steganalysis Score</span>
              <span className="text-2xl font-bold text-cyan-400 mt-1 block">
                {results.analysis.detection_confidence}%
              </span>
              <span className="text-xs text-slate-500">Chi-Square: {results.analysis.chi_square_stat}</span>
            </div>
          </div>

          <div>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-2">
              Recovered Plaintext:
            </span>
            <div className="p-4 bg-slate-900 border border-slate-700 rounded-lg text-emerald-300 font-mono text-sm break-all">
              {results.extract.message}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
