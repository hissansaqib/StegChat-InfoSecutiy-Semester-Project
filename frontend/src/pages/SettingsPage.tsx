import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';

export const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'security' | 'sessions' | 'activity' | 'crypto'>('security');
  
  // Settings & Crypto
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Change Password Form
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [pwdError, setPwdError] = useState('');
  const [pwdSuccess, setPwdSuccess] = useState('');
  const [pwdSubmitting, setPwdSubmitting] = useState(false);

  // Sessions
  const [sessions, setSessions] = useState<any[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionActionMsg, setSessionActionMsg] = useState('');

  // Activity Log
  const [activity, setActivity] = useState<any[]>([]);
  const [activityLoading, setActivityLoading] = useState(false);

  useEffect(() => {
    api.getCryptoSettings()
      .then(setSettings)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const loadSessions = () => {
    setSessionsLoading(true);
    api.listSessions()
      .then((res: any) => setSessions(res.sessions || []))
      .catch(console.error)
      .finally(() => setSessionsLoading(false));
  };

  const loadActivity = () => {
    setActivityLoading(true);
    api.getActivity(50)
      .then((res: any) => setActivity(res.activity || []))
      .catch(console.error)
      .finally(() => setActivityLoading(false));
  };

  useEffect(() => {
    if (activeTab === 'sessions') {
      loadSessions();
    } else if (activeTab === 'activity') {
      loadActivity();
    }
  }, [activeTab]);

  // Password Policy Checks
  const hasLength = newPassword.length >= 10;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasDigit = /\d/.test(newPassword);
  const passwordsMatch = newPassword && confirmNewPassword && newPassword === confirmNewPassword;
  const isNewPasswordValid = hasLength && hasUpper && hasLower && hasDigit;

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwdError('');
    setPwdSuccess('');

    if (!currentPassword) {
      setPwdError('Please enter your current password.');
      return;
    }

    if (!isNewPasswordValid) {
      setPwdError('New password must be at least 10 characters long and include an uppercase letter, lowercase letter, and a number.');
      return;
    }

    if (newPassword !== confirmNewPassword) {
      setPwdError('New passwords do not match.');
      return;
    }

    setPwdSubmitting(true);
    try {
      const res = await api.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPwdSuccess(res.message || 'Password changed successfully! Other sessions have been revoked.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
    } catch (err: any) {
      setPwdError(err.message || 'Failed to update password.');
    } finally {
      setPwdSubmitting(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await api.revokeSession(sessionId);
      setSessionActionMsg('Session revoked successfully.');
      loadSessions();
      setTimeout(() => setSessionActionMsg(''), 4000);
    } catch (err: any) {
      setSessionActionMsg(err.message || 'Failed to revoke session.');
    }
  };

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
        <h1 className="text-2xl font-bold text-white tracking-tight">Account & Security Settings</h1>
        <p className="text-xs text-slate-400 mt-1">
          Manage your credentials, active sessions, audit activity, and inspect platform cryptographic guarantees.
        </p>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-1">
        <button
          onClick={() => setActiveTab('security')}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition border-b-2 ${
            activeTab === 'security'
              ? 'border-indigo-500 text-indigo-400 bg-slate-900/40'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          🔐 Password & Credentials
        </button>
        <button
          onClick={() => setActiveTab('sessions')}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition border-b-2 ${
            activeTab === 'sessions'
              ? 'border-indigo-500 text-indigo-400 bg-slate-900/40'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          💻 Active Sessions
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition border-b-2 ${
            activeTab === 'activity'
              ? 'border-indigo-500 text-indigo-400 bg-slate-900/40'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          📋 Security Audit Log
        </button>
        <button
          onClick={() => setActiveTab('crypto')}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition border-b-2 ${
            activeTab === 'crypto'
              ? 'border-indigo-500 text-indigo-400 bg-slate-900/40'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          🛡️ Encryption & Architecture
        </button>
      </div>

      {/* TAB 1: Password & Credentials */}
      {activeTab === 'security' && (
        <div className="space-y-6">
          {/* User Profile Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4">
              Authenticated Profile
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
              <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700/60">
                <span className="text-slate-400 uppercase tracking-wider block text-[10px]">Username</span>
                <span className="text-white font-mono font-bold text-sm mt-0.5 block">{user?.username}</span>
              </div>
              <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700/60">
                <span className="text-slate-400 uppercase tracking-wider block text-[10px]">Email Address</span>
                <span className="text-white font-mono font-medium text-sm mt-0.5 block">{user?.email || 'None'}</span>
              </div>
              <div className="p-3 bg-slate-800/60 rounded-xl border border-slate-700/60">
                <span className="text-slate-400 uppercase tracking-wider block text-[10px]">Display Name</span>
                <span className="text-white font-bold text-sm mt-0.5 block">{user?.display_name}</span>
              </div>
            </div>
          </div>

          {/* Change Password Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-1">
              Change Account Password
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Updating your password immediately hashes the credential with Argon2id and revokes all other active sessions server-side.
            </p>

            {pwdError && (
              <div className="mb-4 p-3 bg-rose-950/70 border border-rose-500/40 text-rose-200 text-xs rounded-xl flex items-center gap-2">
                <span>⚠️</span>
                <span>{pwdError}</span>
              </div>
            )}

            {pwdSuccess && (
              <div className="mb-4 p-3 bg-emerald-950/70 border border-emerald-500/40 text-emerald-200 text-xs rounded-xl flex items-center gap-2">
                <span>✓</span>
                <span>{pwdSuccess}</span>
              </div>
            )}

            <form onSubmit={handleChangePassword} className="space-y-4 max-w-lg">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Current Password
                </label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  New Password
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Min 10 chars, upper, lower, number"
                  className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
              </div>

              {/* Password Policy Guidance */}
              {newPassword && (
                <div className="p-3 bg-slate-800/60 border border-slate-700/50 rounded-xl text-xs space-y-1">
                  <div className="font-semibold text-slate-300 mb-1">New Password Requirements:</div>
                  <div className="grid grid-cols-2 gap-1 text-[11px]">
                    <span className={hasLength ? 'text-emerald-400 font-medium' : 'text-slate-400'}>
                      {hasLength ? '✓' : '○'} At least 10 characters
                    </span>
                    <span className={hasUpper ? 'text-emerald-400 font-medium' : 'text-slate-400'}>
                      {hasUpper ? '✓' : '○'} Uppercase letter (A-Z)
                    </span>
                    <span className={hasLower ? 'text-emerald-400 font-medium' : 'text-slate-400'}>
                      {hasLower ? '✓' : '○'} Lowercase letter (a-z)
                    </span>
                    <span className={hasDigit ? 'text-emerald-400 font-medium' : 'text-slate-400'}>
                      {hasDigit ? '✓' : '○'} Number (0-9)
                    </span>
                  </div>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                />
                {confirmNewPassword && (
                  <div className={`mt-1 text-[11px] ${passwordsMatch ? 'text-emerald-400 font-medium' : 'text-rose-400'}`}>
                    {passwordsMatch ? '✓ Passwords match' : '✗ Passwords do not match'}
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={pwdSubmitting || !isNewPasswordValid || !passwordsMatch}
                className="py-2.5 px-5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
              >
                {pwdSubmitting ? 'Updating Password & Revoking Sessions...' : 'Update Password'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* TAB 2: Active Sessions */}
      {activeTab === 'sessions' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Active Browser Sessions
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Each session is identified by a cryptographically secure 256-bit token; only the SHA-256 hash is held in storage.
              </p>
            </div>
            <button
              onClick={loadSessions}
              className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
            >
              Refresh
            </button>
          </div>

          {sessionActionMsg && (
            <div className="mb-4 p-3 bg-indigo-950/70 border border-indigo-500/40 text-indigo-200 text-xs rounded-xl">
              {sessionActionMsg}
            </div>
          )}

          {sessionsLoading ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading sessions...</div>
          ) : sessions.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">No active sessions found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                    <th className="py-2.5 px-3">Session Hash</th>
                    <th className="py-2.5 px-3">IP Address</th>
                    <th className="py-2.5 px-3">User Agent</th>
                    <th className="py-2.5 px-3">Created</th>
                    <th className="py-2.5 px-3">Expires</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                  {sessions.map((sess) => (
                    <tr key={sess.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-3">
                        <span className="text-indigo-400 font-bold">{sess.token_hash_preview}</span>
                        {sess.is_current && (
                          <span className="ml-2 px-2 py-0.5 bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 rounded text-[10px] font-sans font-bold">
                            CURRENT
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3">{sess.ip_address || '127.0.0.1'}</td>
                      <td className="py-3 px-3 max-w-xs truncate text-[11px] font-sans text-slate-400" title={sess.user_agent}>
                        {sess.user_agent || 'Unknown Client'}
                      </td>
                      <td className="py-3 px-3 text-[11px]">{new Date(sess.created_at).toLocaleString()}</td>
                      <td className="py-3 px-3 text-[11px] text-slate-400">{new Date(sess.expires_at).toLocaleDateString()}</td>
                      <td className="py-3 px-3 text-right">
                        {sess.is_current ? (
                          <span className="text-[11px] text-slate-500 italic">This Device</span>
                        ) : (
                          <button
                            onClick={() => handleRevokeSession(sess.id)}
                            className="px-2.5 py-1 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded text-[11px] font-sans transition"
                          >
                            Revoke
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Security Audit Log */}
      {activeTab === 'activity' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Security Audit Trail
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Immutable security logs detailing authentication attempts, OTP checks, credential changes, and session events.
              </p>
            </div>
            <button
              onClick={loadActivity}
              className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
            >
              Refresh
            </button>
          </div>

          {activityLoading ? (
            <div className="py-8 text-center text-xs text-slate-400">Loading audit records...</div>
          ) : activity.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-500">No activity logged yet.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                    <th className="py-2.5 px-3">Timestamp</th>
                    <th className="py-2.5 px-3">Event</th>
                    <th className="py-2.5 px-3">IP Address</th>
                    <th className="py-2.5 px-3">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                  {activity.map((act) => (
                    <tr key={act.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-2.5 px-3 text-[11px] text-slate-400 whitespace-nowrap">
                        {new Date(act.created_at).toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          act.action.includes('FAIL') || act.action.includes('EXCEEDED')
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                            : act.action.includes('SUCCESS') || act.action.includes('REGISTERED')
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                            : 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40'
                        }`}>
                          {act.action}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-[11px]">{act.ip_address || '127.0.0.1'}</td>
                      <td className="py-2.5 px-3 text-[11px] text-slate-400">
                        {act.detail ? JSON.stringify(act.detail) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Encryption Architecture */}
      {activeTab === 'crypto' && (
        <div className="space-y-6">
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
      )}
    </div>
  );
};
