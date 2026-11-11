const BASE_URL = '/api/v1';

async function fetchJson(endpoint: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    credentials: 'include',
  });

  if (!res.ok) {
    let errorDetail = 'Request failed';
    try {
      const err = await res.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch {
      errorDetail = res.statusText;
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Auth with MFA
  register: (data: { username: string; email: string; display_name: string; password: string }) =>
    fetchJson('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data: { username_or_email: string; password: string }) =>
    fetchJson('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  verifyOtp: (data: { verification_id: string; otp_code: string }) =>
    fetchJson('/auth/verify-otp', { method: 'POST', body: JSON.stringify(data) }),
  resendOtp: (data: { verification_id: string }) =>
    fetchJson('/auth/resend-otp', { method: 'POST', body: JSON.stringify(data) }),
  logout: () =>
    fetchJson('/auth/logout', { method: 'POST' }),
  me: () =>
    fetchJson('/auth/me'),

  // Carriers & Lab
  listCarriers: () =>
    fetchJson('/carriers'),
  labEmbed: (data: { carrier_id: string; message: string; key?: string }) =>
    fetchJson('/lab/embed', { method: 'POST', body: JSON.stringify(data) }),
  labExtract: (data: { carrier_id: string; carrier_bytes: string; key?: string }) =>
    fetchJson('/lab/extract', { method: 'POST', body: JSON.stringify(data) }),

  // Conversations & Chat
  listConversations: () =>
    fetchJson('/conversations'),
  createConversation: (data: { participant_id?: string; title?: string }) =>
    fetchJson('/conversations', { method: 'POST', body: JSON.stringify(data) }),
  listMessages: (convId: string) =>
    fetchJson(`/conversations/${convId}/messages`),
  sendMessage: (convId: string, data: { content: string; carrier_id?: string; carrier_bytes?: string; is_stego?: boolean }) =>
    fetchJson(`/conversations/${convId}/messages`, { method: 'POST', body: JSON.stringify(data) }),
  listUsers: () =>
    fetchJson('/users'),

  // Bench
  runBench: (data: { carrier_id: string; payload_size: number; iterations: number; name?: string }) =>
    fetchJson('/bench/run', { method: 'POST', body: JSON.stringify(data) }),
  listBenchSuites: () =>
    fetchJson('/bench/suites'),

  // Analysis
  runAnalysis: (data: { carrier_bytes: string; carrier_id?: string }) =>
    fetchJson('/analysis/run', { method: 'POST', body: JSON.stringify(data) }),
  listAnalysisResults: () =>
    fetchJson('/analysis/results'),

  // Recommendations & Reports
  getRecommendations: (data: { payload_bytes: number; min_recovery_rate?: number; allowed_kinds?: string[] }) =>
    fetchJson('/recommend', { method: 'POST', body: JSON.stringify(data) }),
  listRuns: () =>
    fetchJson('/reports/runs'),
  getRun: (id: string) =>
    fetchJson(`/reports/runs/${id}`),
};
