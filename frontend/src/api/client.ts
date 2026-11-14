const BASE_URL = '/api/v1';

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
  return match ? decodeURIComponent(match[3]) : null;
}

async function fetchJson(endpoint: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  // Add CSRF token for state-changing operations
  const method = (options.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCookie('stegchat_csrf');
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      headers,
      credentials: 'include',
    });
  } catch (netErr: any) {
    throw new Error('Backend server is unreachable. Please verify StegChat backend is running.');
  }

  if (!res.ok) {
    let errorDetail = 'Request failed';
    try {
      const err = await res.json();
      if (err.error && err.error.message) {
        errorDetail = err.error.message;
      } else if (err.detail) {
        errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
      } else {
        errorDetail = JSON.stringify(err);
      }
    } catch {
      errorDetail = res.statusText || `Request failed with status ${res.status}`;
    }

    if (res.status === 401 && !endpoint.startsWith('/auth/login') && !endpoint.startsWith('/auth/register')) {
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
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
  changePassword: (data: { current_password: string; new_password: string }) =>
    fetchJson('/auth/change-password', { method: 'POST', body: JSON.stringify(data) }),
  listSessions: () =>
    fetchJson('/auth/sessions'),
  revokeSession: (sessionId: string) =>
    fetchJson(`/auth/sessions/${sessionId}`, { method: 'DELETE' }),
  getActivity: (limit?: number) =>
    fetchJson(`/auth/activity${limit ? `?limit=${limit}` : ''}`),

  // Crypto & Settings
  listCryptoAlgorithms: () =>
    fetchJson('/crypto/algorithms'),
  getCryptoSettings: () =>
    fetchJson('/crypto/settings'),

  // Carriers & Lab
  listCarriers: () =>
    fetchJson('/carriers'),
  getCarrierCapacity: (carrierId: string) =>
    fetchJson(`/carriers/${carrierId}/capacity`, { method: 'POST' }),
  labEmbed: (data: { carrier_id: string; message: string; algorithm?: string; passphrase?: string; seed?: string }) =>
    fetchJson('/lab/embed', { method: 'POST', body: JSON.stringify(data) }),
  labExtract: (data: { carrier_id: string; carrier_bytes: string; passphrase?: string; seed?: string }) =>
    fetchJson('/lab/extract', { method: 'POST', body: JSON.stringify(data) }),

  // Conversations & Chat
  listConversations: () =>
    fetchJson('/conversations'),
  createConversation: (data: { participant_id?: string; title?: string }) =>
    fetchJson('/conversations', { method: 'POST', body: JSON.stringify(data) }),
  listMessages: (convId: string) =>
    fetchJson(`/conversations/${convId}/messages`),
  sendMessage: (convId: string, data: { content: string; carrier_id?: string; carrier_bytes?: string; is_stego?: boolean; algorithm?: string }) =>
    fetchJson(`/conversations/${convId}/messages`, { method: 'POST', body: JSON.stringify(data) }),
  listUsers: () =>
    fetchJson('/users'),

  // Bench
  runBench: (data: { carrier_id: string; payload_size: number; iterations: number; name?: string; algorithm?: string }) =>
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
