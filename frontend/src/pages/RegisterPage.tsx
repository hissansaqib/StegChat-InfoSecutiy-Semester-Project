import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';

export const RegisterPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
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

  const handleInitiateRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // Client-side Validation Checks
    if (!username.trim() || username.length < 3 || username.length > 32) {
      setError('Username must be between 3 and 32 characters long.');
      return;
    }

    if (!/^[a-zA-Z0-9_-]+$/.test(username.trim())) {
      setError('Username can only contain alphanumeric characters, underscores, and hyphens.');
      return;
    }

    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    if (!email.trim() || !emailRegex.test(email.trim())) {
      setError('Please provide a valid email address (e.g. user@domain.com).');
      return;
    }

    if (!displayName.trim() || displayName.length < 2) {
      setError('Display name must be at least 2 characters long.');
      return;
    }

    if (password.length < 8) {
      setError('Password must contain at least 8 characters.');
      return;
    }

    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setError('Password must contain at least one letter and at least one number.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please re-enter your password.');
      return;
    }

    setSubmitting(true);
    try {
      const res = await api.register({
        username: username.trim(),
        email: email.trim(),
        display_name: displayName.trim(),
        password: password,
      });

      if (res.status === 'mfa_required') {
        setVerificationId(res.verification_id);
        setTargetEmail(res.email);
        setDevHint(res.dev_hint || '');
        setMfaStep(true);
      }
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please review your input.');
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
      <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-lg bg-slate-900/80 backdrop-blur-xl border border-slate-700/60 rounded-2xl p-8 shadow-2xl relative z-10">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-cyan-500 text-white mb-4 shadow-lg shadow-indigo-500/20">
            <span className="text-2xl font-bold">✨</span>
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">
            {mfaStep ? 'Verify Your Email Address' : 'Create Your StegChat Account'}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {mfaStep
              ? `We sent a 6-digit confirmation code to ${targetEmail}`
              : 'Join the next generation of privacy-preserving covert communications'}
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
          /* Registration Form */
          <form onSubmit={handleInitiateRegister} className="space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. alice_01"
                  className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition placeholder:text-slate-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Alice Smith"
                  className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition placeholder:text-slate-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                Email Address (One Account per Email)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="alice@example.com"
                className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition placeholder:text-slate-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min 8 chars, 1 letter, 1 num"
                  className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition placeholder:text-slate-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Confirm Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition placeholder:text-slate-500"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full mt-3 py-3 px-4 bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-500 hover:from-indigo-500 hover:to-cyan-400 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
            >
              {submitting ? 'Creating Account & Dispatching OTP...' : 'Send Verification Code (MFA)'}
            </button>
          </form>
        ) : (
          /* Step 2: MFA OTP Verification */
          <form onSubmit={handleVerifyOtp} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 text-center">
                Enter 6-Digit Email Verification Code
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
              {submitting ? 'Finalizing Registration...' : 'Verify Code & Complete Account'}
            </button>

            <div className="flex justify-between items-center pt-2 text-xs">
              <button
                type="button"
                onClick={() => setMfaStep(false)}
                className="text-slate-400 hover:text-white transition"
              >
                &larr; Back to edit details
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
          Already have an account?{' '}
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-4">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
