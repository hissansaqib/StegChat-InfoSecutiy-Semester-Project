import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export const StegoBenchPage: React.FC = () => {
  const [carrierId, setCarrierId] = useState('png_lsb');
  const [payloadSize, setPayloadSize] = useState(128);
  const [iterations, setIterations] = useState(5);
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  const loadHistory = async () => {
    try {
      const data = await api.listBenchSuites();
      setHistory(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    try {
      await api.runBench({
        carrier_id: carrierId,
        payload_size: payloadSize,
        iterations: iterations,
        name: `Bench ${carrierId.toUpperCase()} @ ${payloadSize}B`,
      });
      await loadHistory();
    } catch (err: any) {
      alert('Bench failed: ' + err.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">StegoBench Benchmarking Suite</h1>
        <p className="text-sm text-slate-400 mt-1">
          Measure throughput, bit-recovery fidelity, and CPU overhead across simulated iterations.
        </p>
      </div>

      {/* Control panel */}
      <form onSubmit={handleRun} className="bg-slate-850 p-6 rounded-xl border border-slate-800 space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Carrier
            </label>
            <select
              value={carrierId}
              onChange={(e) => setCarrierId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
            >
              <option value="png_lsb">PNG Image LSB</option>
              <option value="wav_lsb">WAV Audio LSB</option>
              <option value="fake">Fake XOR Carrier</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Payload Size (Bytes)
            </label>
            <input
              type="number"
              min="16"
              max="65536"
              value={payloadSize}
              onChange={(e) => setPayloadSize(Number(e.target.value))}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Iterations (Samples)
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={iterations}
              onChange={(e) => setIterations(Number(e.target.value))}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={running}
          className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition disabled:opacity-50"
        >
          {running ? 'Running Benchmark Iterations...' : 'Execute Benchmark'}
        </button>
      </form>

      {/* Results table */}
      <div className="bg-slate-850 rounded-xl border border-slate-800 overflow-hidden">
        <div className="p-4 border-b border-slate-800">
          <h2 className="font-semibold text-white">Benchmark History</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800 text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="p-3">Suite Name</th>
                <th className="p-3">Carrier</th>
                <th className="p-3">Payload</th>
                <th className="p-3">Embed Latency</th>
                <th className="p-3">Extract Latency</th>
                <th className="p-3">Recovery Rate</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {history.map((row) => (
                <tr key={row.id} className="hover:bg-slate-800/40">
                  <td className="p-3 font-medium text-white">{row.name}</td>
                  <td className="p-3 font-mono text-xs">{row.carrier_id}</td>
                  <td className="p-3">{row.payload_size} bytes</td>
                  <td className="p-3">{row.embed_time_ms_mean} ms</td>
                  <td className="p-3">{row.extract_time_ms_mean} ms</td>
                  <td className="p-3 font-bold text-emerald-400">
                    {(row.recovery_rate * 100).toFixed(0)}%
                  </td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 text-xs bg-emerald-500/20 text-emerald-300 rounded border border-emerald-500/30">
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={7} className="p-4 text-center text-slate-500">
                    No benchmarks run yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
