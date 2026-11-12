import React, { useState } from 'react';

const BASE_URL = '/api/v1';

export const HashToolPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'digest' | 'verify' | 'hmac' | 'compare'>('digest');

  // Tab 1: Digest
  const [inputType, setInputType] = useState<'text' | 'file'>('text');
  const [inputText, setInputText] = useState('StegChat integrity and cryptographic hash verification sample.');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAlgs, setSelectedAlgs] = useState<string[]>(['sha256', 'sha512', 'sha3_256', 'blake2b']);
  const [digestResults, setDigestResults] = useState<any>(null);
  const [digestLoading, setDigestLoading] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Tab 2: Verify
  const [verifyInputType, setVerifyInputType] = useState<'text' | 'file'>('text');
  const [verifyText, setVerifyText] = useState('');
  const [verifyFile, setVerifyFile] = useState<File | null>(null);
  const [expectedHash, setExpectedHash] = useState('');
  const [verifyAlg, setVerifyAlg] = useState('sha256');
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [verifyLoading, setVerifyLoading] = useState(false);

  // Tab 3: HMAC
  const [hmacText, setHmacText] = useState('Confidential message payload to authenticate');
  const [hmacKey, setHmacKey] = useState('my_secret_authentication_key_123');
  const [hmacResult, setHmacResult] = useState<string | null>(null);
  const [hmacExpected, setHmacExpected] = useState('');
  const [hmacMatch, setHmacMatch] = useState<boolean | null>(null);

  // Tab 4: Compare Two Files
  const [fileA, setFileA] = useState<File | null>(null);
  const [fileB, setFileB] = useState<File | null>(null);
  const [compareAlg, setCompareAlg] = useState('sha256');
  const [compareResult, setCompareResult] = useState<any>(null);
  const [compareLoading, setCompareLoading] = useState(false);

  // Digest submit
  const handleComputeDigests = async () => {
    setDigestLoading(true);
    setDigestResults(null);
    try {
      const formData = new FormData();
      if (inputType === 'file' && selectedFile) {
        formData.append('file', selectedFile);
      } else {
        formData.append('text', inputText);
      }
      formData.append('algorithms', selectedAlgs.join(','));

      const res = await fetch(`${BASE_URL}/integrity/hash`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setDigestResults(data.digests);
    } catch (err: any) {
      alert('Hashing failed: ' + err.message);
    } finally {
      setDigestLoading(false);
    }
  };

  // Verify submit
  const handleVerify = async () => {
    setVerifyLoading(true);
    setVerifyResult(null);
    try {
      const formData = new FormData();
      if (verifyInputType === 'file' && verifyFile) {
        formData.append('file', verifyFile);
      } else {
        formData.append('text', verifyText);
      }
      formData.append('expected_digest', expectedHash.trim());
      formData.append('algorithm', verifyAlg);

      const res = await fetch(`${BASE_URL}/integrity/verify`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      setVerifyResult(data);
    } catch (err: any) {
      alert('Verification failed: ' + err.message);
    } finally {
      setVerifyLoading(false);
    }
  };

  // HMAC generate
  const handleGenerateHmac = async () => {
    try {
      const res = await fetch(`${BASE_URL}/integrity/hmac`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: hmacText, key: hmacKey }),
      });
      const data = await res.json();
      setHmacResult(data.hmac);
    } catch (err: any) {
      alert('HMAC failed: ' + err.message);
    }
  };

  // HMAC verify
  const handleVerifyHmac = async () => {
    try {
      const res = await fetch(`${BASE_URL}/integrity/hmac/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: hmacText, key: hmacKey, expected_hmac: hmacExpected.trim() }),
      });
      const data = await res.json();
      setHmacMatch(data.matches);
    } catch (err: any) {
      alert('HMAC verify failed: ' + err.message);
    }
  };

  // Compare files
  const handleCompareFiles = async () => {
    if (!fileA || !fileB) return;
    setCompareLoading(true);
    setCompareResult(null);
    try {
      const fdA = new FormData();
      fdA.append('file', fileA);
      fdA.append('algorithms', compareAlg);
      const resA = await fetch(`${BASE_URL}/integrity/hash`, { method: 'POST', body: fdA }).then((r) => r.json());

      const fdB = new FormData();
      fdB.append('file', fileB);
      fdB.append('algorithms', compareAlg);
      const resB = await fetch(`${BASE_URL}/integrity/hash`, { method: 'POST', body: fdB }).then((r) => r.json());

      const hashA = resA.digests[compareAlg].digest;
      const hashB = resB.digests[compareAlg].digest;

      setCompareResult({
        fileA: { name: fileA.name, size: fileA.size, hash: hashA },
        fileB: { name: fileB.name, size: fileB.size, hash: hashB },
        match: hashA.toLowerCase() === hashB.toLowerCase(),
      });
    } catch (err: any) {
      alert('File comparison failed: ' + err.message);
    } finally {
      setCompareLoading(false);
    }
  };

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <span>🛡️</span> Cryptographic Hash & Integrity Diagnostic Tool
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Perform multi-algorithm digests (SHA-256, SHA-512, SHA3-256, BLAKE2b), HMAC-SHA256, and constant-time integrity verification.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 space-x-2">
        {[
          { id: 'digest', label: 'Hash Generator', icon: '⚡' },
          { id: 'verify', label: 'Verify Digest', icon: '🔍' },
          { id: 'hmac', label: 'HMAC-SHA256', icon: '🔑' },
          { id: 'compare', label: 'Compare Two Files', icon: '⚖️' },
        ].map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id as any)}
            className={`px-4 py-2.5 text-xs font-semibold rounded-t-xl transition flex items-center gap-2 border-b-2 ${
              activeTab === t.id
                ? 'bg-slate-900 border-indigo-500 text-indigo-300'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>{t.icon}</span>
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      {/* Tab 1: Digest Generator */}
      {activeTab === 'digest' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-5">
          <div className="flex items-center gap-4">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Input Source:</span>
            <div className="flex gap-2">
              <button
                onClick={() => setInputType('text')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  inputType === 'text' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                Raw Text
              </button>
              <button
                onClick={() => setInputType('file')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                  inputType === 'file' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                File Upload
              </button>
            </div>
          </div>

          {inputType === 'text' ? (
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Text Payload
              </label>
              <textarea
                rows={3}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white font-mono text-xs focus:outline-none focus:border-indigo-500"
              />
            </div>
          ) : (
            <div className="p-4 bg-slate-800/50 border border-dashed border-slate-700 rounded-xl text-center">
              <input
                type="file"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                className="text-xs text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
              />
              {selectedFile && (
                <div className="text-xs text-slate-400 font-mono mt-2">
                  Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                </div>
              )}
            </div>
          )}

          {/* Algorithm Multi-Select */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Select Algorithms
            </label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {['sha256', 'sha512', 'sha3_256', 'blake2b'].map((alg) => {
                const active = selectedAlgs.includes(alg);
                return (
                  <button
                    key={alg}
                    type="button"
                    onClick={() => {
                      if (active) {
                        if (selectedAlgs.length > 1) setSelectedAlgs(selectedAlgs.filter((a) => a !== alg));
                      } else {
                        setSelectedAlgs([...selectedAlgs, alg]);
                      }
                    }}
                    className={`px-3 py-2 rounded-xl text-xs font-mono font-bold transition border ${
                      active
                        ? 'bg-indigo-600/30 border-indigo-500 text-indigo-300'
                        : 'bg-slate-800/60 border-slate-700 text-slate-400'
                    }`}
                  >
                    {alg.toUpperCase()}
                  </button>
                );
              })}
            </div>
          </div>

          <button
            onClick={handleComputeDigests}
            disabled={digestLoading}
            className="w-full py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 text-white font-bold rounded-xl text-xs shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
          >
            {digestLoading ? 'Streaming & Computing Digests...' : 'Generate Cryptographic Digests'}
          </button>

          {/* Results Display */}
          {digestResults && (
            <div className="space-y-3 pt-3 border-t border-slate-800">
              {Object.entries(digestResults).map(([alg, data]: [string, any]) => (
                <div key={alg} className="p-3.5 bg-slate-800/60 border border-slate-700 rounded-xl space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-300 font-mono uppercase">{alg}</span>
                    <span className="text-[10px] text-slate-400 font-mono">{data.duration_ms} ms</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      readOnly
                      value={data.digest}
                      className="flex-1 px-3 py-1 bg-slate-950/80 border border-slate-800 rounded-lg text-xs font-mono text-emerald-300 select-all"
                    />
                    <button
                      onClick={() => copyToClipboard(data.digest, alg)}
                      className="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-[10px] font-semibold transition"
                    >
                      {copiedKey === alg ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Verify Digest */}
      {activeTab === 'verify' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-4">
          <div className="flex items-center gap-4">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Target:</span>
            <div className="flex gap-2">
              <button
                onClick={() => setVerifyInputType('text')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  verifyInputType === 'text' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                Text
              </button>
              <button
                onClick={() => setVerifyInputType('file')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                  verifyInputType === 'file' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
                }`}
              >
                File
              </button>
            </div>
          </div>

          {verifyInputType === 'text' ? (
            <textarea
              rows={2}
              value={verifyText}
              onChange={(e) => setVerifyText(e.target.value)}
              placeholder="Enter text to verify..."
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white font-mono text-xs"
            />
          ) : (
            <input
              type="file"
              onChange={(e) => setVerifyFile(e.target.files?.[0] || null)}
              className="text-xs text-slate-300"
            />
          )}

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Expected Hash Digest
              </label>
              <input
                type="text"
                value={expectedHash}
                onChange={(e) => setExpectedHash(e.target.value)}
                placeholder="Paste expected hex hash (e.g. from Get-FileHash)..."
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white font-mono text-xs"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Algorithm
              </label>
              <select
                value={verifyAlg}
                onChange={(e) => setVerifyAlg(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white text-xs font-mono"
              >
                <option value="sha256">SHA-256</option>
                <option value="sha512">SHA-512</option>
                <option value="sha3_256">SHA3-256</option>
                <option value="blake2b">BLAKE2b</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleVerify}
            disabled={verifyLoading || !expectedHash.trim()}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition disabled:opacity-50"
          >
            {verifyLoading ? 'Verifying...' : 'Execute Constant-Time Verification'}
          </button>

          {verifyResult && (
            <div
              className={`p-4 rounded-xl border text-xs font-mono space-y-1 ${
                verifyResult.matches
                  ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-200'
                  : 'bg-rose-950/60 border-rose-500/50 text-rose-200'
              }`}
            >
              <div className="flex items-center justify-between font-bold text-sm">
                <span>{verifyResult.matches ? 'MATCH (INTEGRITY CONFIRMED)' : 'MISMATCH (TAMPERING DETECTED)'}</span>
                <span className="text-xs">{verifyResult.algorithm.toUpperCase()}</span>
              </div>
              <div className="pt-2 text-[11px] space-y-1">
                <div>Expected: {verifyResult.expected_digest}</div>
                <div>Computed: {verifyResult.actual_digest}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: HMAC */}
      {activeTab === 'hmac' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Message Content
            </label>
            <textarea
              rows={2}
              value={hmacText}
              onChange={(e) => setHmacText(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white font-mono text-xs"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
              Secret Key
            </label>
            <input
              type="text"
              value={hmacKey}
              onChange={(e) => setHmacKey(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl text-white font-mono text-xs"
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleGenerateHmac}
              className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition"
            >
              Compute HMAC-SHA256
            </button>
          </div>

          {hmacResult && (
            <div className="p-3.5 bg-slate-800/80 border border-slate-700 rounded-xl space-y-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Generated HMAC-SHA256 Digest:
              </span>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={hmacResult}
                  className="flex-1 px-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-emerald-300"
                />
                <button
                  onClick={() => copyToClipboard(hmacResult, 'hmac')}
                  className="px-2.5 py-1 bg-slate-700 text-white text-[10px] rounded"
                >
                  {copiedKey === 'hmac' ? 'Copied' : 'Copy'}
                </button>
              </div>

              <div className="pt-2 border-t border-slate-700/60 flex gap-2">
                <input
                  type="text"
                  placeholder="Paste HMAC to verify..."
                  value={hmacExpected}
                  onChange={(e) => setHmacExpected(e.target.value)}
                  className="flex-1 px-3 py-1 bg-slate-900 border border-slate-700 rounded text-xs font-mono text-white"
                />
                <button
                  onClick={handleVerifyHmac}
                  className="px-3 py-1 bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold rounded"
                >
                  Verify HMAC
                </button>
              </div>

              {hmacMatch !== null && (
                <div
                  className={`p-2 rounded text-xs font-bold text-center ${
                    hmacMatch ? 'bg-emerald-950 text-emerald-300' : 'bg-rose-950 text-rose-300'
                  }`}
                >
                  {hmacMatch ? '✓ HMAC Authenticated' : '✗ HMAC Signature Invalid'}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Compare Two Files */}
      {activeTab === 'compare' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-slate-800/60 border border-slate-700 rounded-xl space-y-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">File A (Reference)</span>
              <input type="file" onChange={(e) => setFileA(e.target.files?.[0] || null)} className="text-xs text-slate-300" />
              {fileA && <div className="text-[10px] font-mono text-slate-400">{fileA.name} ({fileA.size} B)</div>}
            </div>

            <div className="p-4 bg-slate-800/60 border border-slate-700 rounded-xl space-y-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block">File B (Comparison)</span>
              <input type="file" onChange={(e) => setFileB(e.target.files?.[0] || null)} className="text-xs text-slate-300" />
              {fileB && <div className="text-[10px] font-mono text-slate-400">{fileB.name} ({fileB.size} B)</div>}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <select
              value={compareAlg}
              onChange={(e) => setCompareAlg(e.target.value)}
              className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs font-mono text-white"
            >
              <option value="sha256">SHA-256</option>
              <option value="sha512">SHA-512</option>
              <option value="blake2b">BLAKE2b</option>
            </select>
            <button
              onClick={handleCompareFiles}
              disabled={compareLoading || !fileA || !fileB}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl disabled:opacity-50"
            >
              {compareLoading ? 'Comparing...' : 'Compare File Hashes'}
            </button>
          </div>

          {compareResult && (
            <div
              className={`p-4 rounded-xl border text-xs font-mono space-y-2 ${
                compareResult.match
                  ? 'bg-emerald-950/60 border-emerald-500/50 text-emerald-200'
                  : 'bg-rose-950/60 border-rose-500/50 text-rose-200'
              }`}
            >
              <div className="font-bold text-sm">
                {compareResult.match ? 'IDENTICAL FILES (MATCH)' : 'DIFFERENT FILES (HASH DISCREPANCY)'}
              </div>
              <div className="text-[11px] space-y-1">
                <div>File A ({compareResult.fileA.name}): {compareResult.fileA.hash}</div>
                <div>File B ({compareResult.fileB.name}): {compareResult.fileB.hash}</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

