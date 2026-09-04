/**
 * AI-IaC Guard — API Service
 *
 * All calls go to the backend via Vite's proxy (or directly to localhost:8000).
 * No API keys are ever sent from the frontend — keys live only in backend .env.
 */

const BASE_URL = '/api';

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });

  const data = await res.json().catch(() => ({ error: 'Invalid response from server' }));

  if (!res.ok) {
    const msg = data?.detail || data?.error || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

export const api = {
  health: () => request('/health'),

  examples: () => request('/examples'),

  scan: (terraform_code) =>
    request('/scan', {
      method: 'POST',
      body: JSON.stringify({ terraform_code }),
    }),

  analyze: (terraform_code, findings) =>
    request('/analyze', {
      method: 'POST',
      body: JSON.stringify({ terraform_code, findings }),
    }),

  verify: (corrected_terraform, original_findings, original_score) =>
    request('/verify', {
      method: 'POST',
      body: JSON.stringify({ corrected_terraform, original_findings, original_score }),
    }),
};
