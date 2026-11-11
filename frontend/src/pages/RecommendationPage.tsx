import React, { useState, useEffect } from 'react';
import { api } from '../api/client';

export const RecommendationPage: React.FC = () => {
  const [payloadBytes, setPayloadBytes] = useState(256);
  const [minRecovery, setMinRecovery] = useState(0.98);
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<any[]>([]);

  const fetchRecommendations = async () => {
    setLoading(true);
    try {
      const res = await api.getRecommendations({
        payload_bytes: payloadBytes,
        min_recovery_rate: minRecovery,
      });
      setRecommendations(res.recommendations);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [payloadBytes, minRecovery]);

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Carrier Recommendation Engine</h1>
        <p className="text-sm text-slate-400 mt-1">
          Algorithmic multi-objective ranking based on capacity overhead, latency, and detectability metrics.
        </p>
      </div>

      <div className="bg-slate-850 p-6 rounded-xl border border-slate-800 grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Target Secret Payload Size (Bytes)
          </label>
          <input
            type="number"
            min="1"
            value={payloadBytes}
            onChange={(e) => setPayloadBytes(Number(e.target.value))}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Minimum Recovery Tolerance ({(minRecovery * 100).toFixed(0)}%)
          </label>
          <input
            type="range"
            min="0.8"
            max="1.0"
            step="0.01"
            value={minRecovery}
            onChange={(e) => setMinRecovery(Number(e.target.value))}
            className="w-full mt-3"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {recommendations.map((rec, idx) => (
          <div
            key={rec.carrier_id}
            className={`p-5 rounded-xl border flex flex-col justify-between ${
              idx === 0
                ? 'bg-indigo-950/40 border-indigo-500 shadow-lg'
                : 'bg-slate-850 border-slate-800'
            }`}
          >
            <div>
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                  {rec.kind}
                </span>
                {idx === 0 && (
                  <span className="text-xs px-2 py-0.5 rounded-full font-bold bg-indigo-500 text-white">
                    TOP CHOICE
                  </span>
                )}
              </div>
              <h3 className="text-lg font-bold text-white">{rec.name}</h3>
              <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                {rec.recommendation_reason}
              </p>
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800 space-y-2 text-xs">
              <div className="flex justify-between text-slate-400">
                <span>Suitability Score</span>
                <span className="font-bold text-emerald-400">{(rec.suitability_score * 100).toFixed(0)}%</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Estimated Speed</span>
                <span className="text-white">{rec.estimated_speed_ms} ms</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>Detectability Risk</span>
                <span className="text-amber-400">{(rec.detectability_score * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

