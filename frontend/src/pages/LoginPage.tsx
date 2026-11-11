import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';

export const LoginPage: React.FC = () => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // MFA State
  const [mfaStep, setMfaStep] = useState(false);
  const [verificationId, setVerificationId] = useState('');
  const [targetEmail, setTargetEmail] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [devHint, setDevHint] = useState('');
  const [resending, setResending] = useState(false);

  const { setUser } = useAuth();
  const navigate = useNavigate();

  const handleInitiateLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!identifier.trim()) {
      setError('Please enter your username or registered email address.');
      return;
    }
    if (!password) {
      setError('Please enter your account password.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.login({
        username_or_email: identifier.trim(),
        password: password,
      });

      if (res.status === 'mfa_required') {
        setVerificationId(res.verification_id);
        setTargetEmail(res.email);
        setDevHint(res.dev_hint || '');
        setMfaStep(true);
      } else if (res.user) {
        setUser(res.user);
        navigate('/chat');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!otpCode.trim() || otpCode.trim().length !== 6) {
      setError('Please enter the complete 6-digit verification code.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.verifyOtp({
        verification_id: verificationId,
        otp_code: otpCode.trim(),
      });
      setUser(res.user);
      navigate('/chat');
    } catch (err: any) {
      setError(err.message || 'Incorrect verification code. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setError('');
    setResending(true);
    try {
      const res = await api.resendOtp({ verification_id: verificationId });
      setDevHint(res.dev_hint || '');
      alert(res.message || 'A fresh verification code has been dispatched.');
    } catch (err: any) {
      setError(err.message || 'Failed to resend code.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 p-4 relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-slate-900/80 backdrop-blur-xl border border-slate-700/60 rounded-2xl p-8 shadow-2xl relative z-10">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/40 text-indigo-400 mb-4 shadow-inner">
            <span className="text-2xl">🛡️</span>
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">
            {mfaStep ? 'Two-Factor Authentication' : 'Welcome to StegChat'}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {mfaStep
              ? `Verification code dispatched to ${targetEmail}`
              : 'Military-grade covert steganographic messaging platform'}
          </p>
        </div>

        {error && (
          <div className="mb-5 p-3.5 bg-rose-950/70 border border-rose-500/40 text-rose-200 text-xs rounded-xl flex items-start gap-2.5 shadow-sm">
            <span className="text-base leading-none">⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {devHint && (
          <div className="mb-5 p-3 bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 text-xs rounded-xl font-mono flex items-center justify-between">
            <span>Dev OTP: <strong>{devHint.split(': ')[-1] || devHint}</strong></span>
            <button
              type="button"
              onClick={() => setOtpCode(devHint.split(': ')[-1]?.trim() || '')}
              className="text-[10px] bg-cyan-800/60 hover:bg-cyan-700 text-cyan-100 px-2 py-0.5 rounded transition"
            >
              Autofill
            </button>
          </div>
        )}

        {!mfaStep ? (
          /* Step 1: Identifier & Password */
          <form onSubmit={handleInitiateLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Username or Email
              </label>
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="e.g. alice or alice@domain.com"
                className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition placeholder:text-slate-500"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Password
                </label>
              </div>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition placeholder:text-slate-500"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full mt-2 py-3 px-4 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
            >
              {submitting ? 'Verifying Credentials...' : 'Sign In with MFA'}
            </button>
          </form>
        ) : (
          /* Step 2: MFA OTP Verification */
          <form onSubmit={handleVerifyOtp} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 text-center">
                Enter 6-Digit Verification Code
              </label>
              <input
                type="text"
                maxLength={6}
                autoFocus
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                placeholder="000000"
                className="w-full px-4 py-3 bg-slate-800/90 border border-indigo-500/60 rounded-xl text-white text-center text-2xl font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
              />
            </div>

            <button
              type="submit"
              disabled={submitting || otpCode.length !== 6}
              className="w-full py-3 px-4 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-emerald-600/30 transition disabled:opacity-50"
            >
              {submitting ? 'Authenticating...' : 'Verify & Continue'}
            </button>

            <div className="flex justify-between items-center pt-2 text-xs">
              <button
                type="button"
                onClick={() => setMfaStep(false)}
                className="text-slate-400 hover:text-white transition"
              >
                &larr; Back to login
              </button>
              <button
                type="button"
                disabled={resending}
                onClick={handleResend}
                className="text-indigo-400 hover:text-indigo-300 font-medium transition disabled:opacity-50"
              >
                {resending ? 'Sending...' : 'Resend Code'}
              </button>
            </div>
          </form>
        )}

        <div className="mt-6 pt-5 border-t border-slate-800/80 text-center text-xs text-slate-400">
          Don't have an account yet?{' '}
          <Link to="/register" className="text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-4">
            Create an account
          </Link>
        </div>
      </div>
    </div>
  );
};
