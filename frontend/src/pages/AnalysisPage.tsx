import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export const AnalysisPage: React.FC = () => {
  const [carrierId, setCarrierId] = useState('png_lsb');
  const [sampleText, setSampleText] = useState('Secret embedded text for steganalysis check');
  const [analyzing, setAnalyzing] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  const loadHistory = async () => {
    try {
      const data = await api.listAnalysisResults();
      setHistory(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setAnalyzing(true);
    try {
      // Create a stego carrier first
      const embed = await api.labEmbed({
        carrier_id: carrierId,
        message: sampleText,
      });

      // Analyze it
      await api.runAnalysis({
        carrier_id: carrierId,
        carrier_bytes: embed.carrier_bytes,
      });

      await loadHistory();
    } catch (err: any) {
      alert('Analysis failed: ' + err.message);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Steganalysis Diagnostic Lab</h1>
        <p className="text-sm text-slate-400 mt-1">
          Perform statistical tests (Chi-Square distribution & Regular/Singular Groups) to evaluate detectability.
        </p>
      </div>

      <form onSubmit={handleAnalyze} className="bg-slate-850 p-6 rounded-xl border border-slate-800 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Target Carrier
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
              Synthesized Payload Content
            </label>
            <input
              type="text"
              value={sampleText}
              onChange={(e) => setSampleText(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white font-mono text-sm"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={analyzing}
          className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg transition disabled:opacity-50"
        >
          {analyzing ? 'Executing Statistical Diagnostic...' : 'Run Statistical Steganalysis'}
        </button>
      </form>

      <div className="bg-slate-850 rounded-xl border border-slate-800 overflow-hidden">
        <div className="p-4 border-b border-slate-800">
          <h2 className="font-semibold text-white">Diagnostic Runs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800 text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="p-3">Target Carrier</th>
                <th className="p-3">Sample Volume</th>
                <th className="p-3">Chi-Square (&chi;&sup2;)</th>
                <th className="p-3">RS Score</th>
                <th className="p-3">Stego Detected</th>
                <th className="p-3">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {history.map((row) => (
                <tr key={row.id} className="hover:bg-slate-800/40">
                  <td className="p-3 font-mono text-xs">{row.carrier_id}</td>
                  <td className="p-3">{row.bytes_analyzed} bytes</td>
                  <td className="p-3">{row.chi_square_stat}</td>
                  <td className="p-3">{row.rs_score}</td>
                  <td className="p-3">
                    <span
                      className={`px-2 py-0.5 text-xs rounded font-bold ${
                        row.stego_detected
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {row.stego_detected ? 'ANOMALY DETECTED' : 'CLEAN'}
                    </span>
                  </td>
                  <td className="p-3 font-semibold text-white">{row.detection_confidence}%</td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-4 text-center text-slate-500">
                    No steganalysis runs conducted yet.
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
