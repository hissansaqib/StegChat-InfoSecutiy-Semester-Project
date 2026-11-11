import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';

export const ChatPage: React.FC = () => {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<any[]>([]);
  const [activeConv, setActiveConv] = useState<any | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [text, setText] = useState('');
  const [carrierId, setCarrierId] = useState('png_lsb');
  const [isStego, setIsStego] = useState(false);
  const [secretText, setSecretText] = useState('');
  const [revealed, setRevealed] = useState<{ [id: string]: string }>({});
  const [loading, setLoading] = useState(false);
  const [users, setUsers] = useState<any[]>([]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
      if (convs.length > 0 && !activeConv) {
        setActiveConv(convs[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadUsers = async () => {
    try {
      const u = await api.listUsers();
      setUsers(u.filter((x: any) => x.id !== user?.id));
    } catch (err) {
      console.error(err);
    }
  };

  const loadMessages = async (convId: string) => {
    try {
      const msgs = await api.listMessages(convId);
      setMessages(msgs);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadConversations();
    loadUsers();
  }, []);

  useEffect(() => {
    if (activeConv) {
      loadMessages(activeConv.id);
      const interval = setInterval(() => loadMessages(activeConv.id), 3000);
      return () => clearInterval(interval);
    }
  }, [activeConv]);

  const handleStartConv = async (participantId: string) => {
    try {
      const res = await api.createConversation({ participant_id: participantId });
      await loadConversations();
      setActiveConv({ id: res.id, name: 'New Chat' });
    } catch (err) {
      console.error(err);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeConv || (!text.trim() && !secretText.trim())) return;

    setLoading(true);
    try {
      let carrierBytes: string | undefined = undefined;

      if (isStego && secretText.trim()) {
        const embedRes = await api.labEmbed({
          carrier_id: carrierId,
          message: secretText,
        });
        carrierBytes = embedRes.carrier_bytes;
      }

      await api.sendMessage(activeConv.id, {
        content: text.trim() || '[Secure Steganographic Medium Transmitted]',
        carrier_id: isStego ? carrierId : undefined,
        carrier_bytes: carrierBytes,
        is_stego: isStego,
      });

      setText('');
      setSecretText('');
      setIsStego(false);
      await loadMessages(activeConv.id);
    } catch (err) {
      alert('Failed to send message: ' + err);
    } finally {
      setLoading(false);
    }
  };

  const handleReveal = async (msgId: string, cId: string, cBytes: string) => {
    try {
      const res = await api.labExtract({
        carrier_id: cId,
        carrier_bytes: cBytes,
      });
      setRevealed((prev) => ({ ...prev, [msgId]: res.message }));
    } catch (err) {
      alert('Failed to extract steganographic message: ' + err);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-900/60 rounded-2xl overflow-hidden border border-slate-800/80 shadow-2xl backdrop-blur-xl">
      {/* Conversation Directory */}
      <div className="w-80 bg-slate-900/90 border-r border-slate-800/80 flex flex-col">
        <div className="p-4 border-b border-slate-800/80 flex justify-between items-center bg-slate-900/40">
          <div className="flex items-center gap-2">
            <span className="text-base">💬</span>
            <h2 className="font-bold text-slate-200 text-sm tracking-tight">Active Channels</h2>
          </div>
          <span className="text-[10px] bg-indigo-500/20 text-indigo-300 font-mono px-2 py-0.5 rounded-full border border-indigo-500/30">
            {conversations.length}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-2.5 space-y-1">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => setActiveConv(c)}
              className={`w-full text-left px-3.5 py-3 rounded-xl text-xs flex flex-col transition duration-150 ${
                activeConv?.id === c.id
                  ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-md shadow-indigo-600/20'
                  : 'text-slate-300 hover:bg-slate-800/70 hover:text-white'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <span className="font-semibold text-sm truncate">{c.name || 'Private Channel'}</span>
                <span className="text-[10px] opacity-60 font-mono">Channel</span>
              </div>
              <span className="text-[10px] opacity-75 font-mono mt-0.5 truncate">{c.id}</span>
            </button>
          ))}
          {conversations.length === 0 && (
            <div className="text-xs text-slate-500 p-6 text-center leading-relaxed">
              No conversations yet. Choose a user below to start messaging.
            </div>
          )}
        </div>

        {/* Start new chat with users */}
        {users.length > 0 && (
          <div className="p-3.5 border-t border-slate-800/80 bg-slate-950/60">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Start Conversation With:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {users.map((u) => (
                <button
                  key={u.id}
                  onClick={() => handleStartConv(u.id)}
                  className="text-xs bg-slate-800 hover:bg-indigo-600 text-slate-300 hover:text-white px-2.5 py-1 rounded-lg border border-slate-700 hover:border-indigo-500 transition shadow-sm"
                >
                  +{u.display_name}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Main Messaging Area */}
      <div className="flex-1 flex flex-col bg-slate-950/80">
        {activeConv ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-slate-800/80 flex justify-between items-center bg-slate-900/60 backdrop-blur-md">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-xs font-bold text-indigo-300">
                  #
                </div>
                <div>
                  <span className="font-bold text-white text-sm block">{activeConv.name || 'Channel'}</span>
                  <span className="text-[10px] text-slate-400 font-mono">End-to-end encrypted session</span>
                </div>
              </div>
            </div>

            {/* Message Feed */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {messages.map((m) => {
                const hasStego = m.payload?.is_stego && m.payload?.carrier_bytes;
                const revealedMsg = revealed[m.id];
                return (
                  <div
                    key={m.id}
                    className={`flex flex-col ${m.is_me ? 'items-end' : 'items-start'}`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-medium text-slate-400">
                        {m.is_me ? 'You' : m.sender_name}
                      </span>
                      <span className="text-[9px] text-slate-500 font-mono">
                        {m.created_at ? new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                      </span>
                    </div>

                    <div
                      className={`max-w-lg p-3.5 rounded-2xl shadow-md ${
                        m.is_me
                          ? 'bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white rounded-br-none'
                          : 'bg-slate-850 text-slate-200 border border-slate-700/80 rounded-bl-none'
                      }`}
                    >
                      <div className="text-sm leading-relaxed">{m.payload?.text}</div>

                      {hasStego && (
                        <div className="mt-3 pt-3 border-t border-slate-700/60 text-xs">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-amber-300 font-semibold flex items-center gap-1.5 text-[11px]">
                              <span>🔒</span>
                              <span>Concealed Steganography ({m.payload?.carrier_id})</span>
                            </span>
                            {!revealedMsg && (
                              <button
                                onClick={() =>
                                  handleReveal(m.id, m.payload.carrier_id, m.payload.carrier_bytes)
                                }
                                className="px-2.5 py-1 bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold rounded-lg text-[10px] uppercase tracking-wider transition shadow-sm"
                              >
                                Extract Payload
                              </button>
                            )}
                          </div>
                          {revealedMsg && (
                            <div className="p-2.5 bg-slate-900/90 border border-amber-500/40 rounded-xl text-amber-200 font-mono text-xs break-all mt-1 shadow-inner">
                              <span className="text-amber-400 font-bold block mb-0.5 text-[10px] uppercase tracking-wider">
                                Extracted Secret Message:
                              </span>
                              {revealedMsg}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs gap-2">
                  <span className="text-3xl">🛡️</span>
                  <span>No communications logged in this channel. Send a message to begin.</span>
                </div>
              )}
            </div>

            {/* Input Composer */}
            <form onSubmit={handleSend} className="p-4 border-t border-slate-800/80 bg-slate-900/70 backdrop-blur-md">
              {isStego && (
                <div className="mb-3 p-3.5 bg-slate-850/90 border border-amber-500/30 rounded-xl space-y-2.5 shadow-lg">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                      <span>🔒</span> Covert Embedding Mode Active
                    </span>
                    <select
                      value={carrierId}
                      onChange={(e) => setCarrierId(e.target.value)}
                      className="bg-slate-900 text-xs text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1 focus:outline-none focus:border-amber-500"
                    >
                      <option value="png_lsb">PNG Image LSB</option>
                      <option value="wav_lsb">WAV Audio LSB</option>
                      <option value="fake">Fake Carrier (XOR)</option>
                    </select>
                  </div>
                  <input
                    type="text"
                    value={secretText}
                    onChange={(e) => setSecretText(e.target.value)}
                    placeholder="Enter confidential secret message to embed into carrier..."
                    className="w-full px-3.5 py-2 bg-slate-900/90 border border-slate-700 rounded-lg text-xs text-amber-200 font-mono focus:outline-none focus:border-amber-400 placeholder:text-slate-500"
                  />
                </div>
              )}

              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsStego(!isStego)}
                  className={`px-3 py-2.5 rounded-xl text-xs font-bold transition border flex items-center gap-1.5 ${
                    isStego
                      ? 'bg-amber-400 text-slate-950 border-amber-400 shadow-md shadow-amber-400/20'
                      : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-750'
                  }`}
                  title="Toggle Covert Steganographic Payload"
                >
                  <span>{isStego ? '🔒' : '🔓'}</span>
                  <span>{isStego ? 'Stego On' : 'Plain Text'}</span>
                </button>

                <input
                  type="text"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={
                    isStego ? 'Visible decoy message...' : 'Type confidential communication...'
                  }
                  className="flex-1 px-4 py-2.5 bg-slate-800/80 border border-slate-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 text-sm placeholder:text-slate-500 transition"
                />

                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold rounded-xl text-xs transition disabled:opacity-50 shadow-md shadow-indigo-600/30"
                >
                  {loading ? 'Processing...' : 'Send'}
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-500 text-xs gap-3">
            <span className="text-4xl opacity-50">💬</span>
            <span>Select a conversation from the sidebar or start a new channel.</span>
          </div>
        )}
      </div>
    </div>
  );
};
