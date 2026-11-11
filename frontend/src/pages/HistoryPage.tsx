import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export const HistoryPage: React.FC = () => {
  const [runs, setRuns] = useState<any[]>([]);

  useEffect(() => {
    api.listRuns().then(setRuns).catch(console.error);
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Experiment History & Artifacts</h1>
        <p className="text-sm text-slate-400 mt-1">
          Review persisted experiment records, embed/extract timings, and telemetry.
        </p>
      </div>

      <div className="bg-slate-850 rounded-xl border border-slate-800 overflow-hidden">
        <div className="p-4 border-b border-slate-800">
          <h2 className="font-semibold text-white">All Logged Experiment Runs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800 text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="p-3">Run ID</th>
                <th className="p-3">Experiment Label</th>
                <th className="p-3">Carrier</th>
                <th className="p-3">Payload</th>
                <th className="p-3">Embed Time</th>
                <th className="p-3">Extract Time</th>
                <th className="p-3">Recovery</th>
                <th className="p-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/40">
                  <td className="p-3 font-mono text-xs text-indigo-400">{r.id}</td>
                  <td className="p-3 font-medium text-white">{r.name}</td>
                  <td className="p-3 font-mono text-xs">{r.carrier_id}</td>
                  <td className="p-3">{r.payload_size} B</td>
                  <td className="p-3">{r.embed_time_ms} ms</td>
                  <td className="p-3">{r.extract_time_ms} ms</td>
                  <td className="p-3 font-bold text-emerald-400">
                    {(r.recovery_rate * 100).toFixed(0)}%
                  </td>
                  <td className="p-3 text-xs text-slate-500">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
