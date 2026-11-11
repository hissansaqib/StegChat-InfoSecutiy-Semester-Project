import React from 'react';
import { Navigate, Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export const Layout: React.FC = () => {
  const { user, logout, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-950 text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-indigo-500 border-t-transparent"></div>
          <span className="text-xs font-mono text-slate-400">Initializing StegChat Security Kernel...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const navItems = [
    { label: 'Conversations', icon: '💬', path: '/chat', desc: 'Covert stego messaging' },
    { label: 'Guided Pipeline', icon: '🚀', path: '/demo', desc: 'End-to-end interactive demo' },
    { label: 'StegoBench', icon: '⚡', path: '/bench', desc: 'Telemetry & performance suite' },
    { label: 'Steganalysis', icon: '🔍', path: '/analysis', desc: 'Statistical anomaly detector' },
    { label: 'Recommender', icon: '🎯', path: '/recommender', desc: 'Carrier optimization engine' },
    { label: 'Experiment History', icon: '📜', path: '/history', desc: 'Artifact logs & telemetry' },
  ];

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-72 bg-slate-900/95 border-r border-slate-800/80 flex flex-col justify-between backdrop-blur-md">
        <div>
          {/* Logo & Brand */}
          <div className="p-5 border-b border-slate-800/80">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                <span className="text-lg">🛡️</span>
              </div>
              <div>
                <h1 className="text-base font-extrabold text-white tracking-tight flex items-center gap-2">
                  StegChat <span className="text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.5 rounded font-mono font-bold">v1.0</span>
                </h1>
                <p className="text-[11px] text-slate-400 mt-0.5">Secure Steganography</p>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <div className="p-3">
            <span className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-2">
              Platform Features
            </span>
            <nav className="space-y-1">
              {navItems.map((item) => {
                const active = location.pathname.startsWith(item.path);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-medium transition duration-150 group ${
                      active
                        ? 'bg-gradient-to-r from-indigo-600/90 to-indigo-700 text-white shadow-md shadow-indigo-600/20'
                        : 'text-slate-300 hover:bg-slate-800/70 hover:text-white'
                    }`}
                  >
                    <span className="text-base leading-none group-hover:scale-110 transition-transform">
                      {item.icon}
                    </span>
                    <div className="flex-1 overflow-hidden">
                      <div className="font-semibold">{item.label}</div>
                      <div className="text-[10px] text-slate-400 truncate opacity-80">{item.desc}</div>
                    </div>
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>

        {/* User Status Bar */}
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-xs font-bold text-indigo-300">
              {user.display_name.charAt(0).toUpperCase()}
            </div>
            <div className="overflow-hidden">
              <div className="text-xs font-semibold text-slate-200 truncate">{user.display_name}</div>
              <div className="text-[10px] text-slate-400 truncate font-mono">@{user.username}</div>
            </div>
          </div>
          <button
            onClick={() => logout()}
            className="text-xs bg-slate-800 hover:bg-rose-600/80 px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white transition border border-slate-700"
            title="Sign out of StegChat"
          >
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content Viewport */}
      <main className="flex-1 overflow-y-auto bg-slate-950 p-8">
        <Outlet />
      </main>
    </div>
  );
};
