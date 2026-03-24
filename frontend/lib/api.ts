import { getCookie } from '@/lib/utils';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type RequestOptions = RequestInit & { csrf?: boolean };

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Accept', 'application/json');

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (options.csrf) {
    const csrf = getCookie('kb_csrf_token');
    if (csrf) {
      headers.set('X-CSRF-Token', csrf);
    }
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include'
  });

  if (!response.ok) {
    const raw = await response.text();
    try {
      const parsed = JSON.parse(raw);
      const detail = typeof parsed?.detail === 'string' ? parsed.detail : raw;
      throw new Error(detail || `Request failed: ${response.status}`);
    } catch {
      throw new Error(raw || `Request failed: ${response.status}`);
    }
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json() as Promise<T>;
  }
  return {} as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body?: unknown, csrf = false) =>
    request<T>(path, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body || {}),
      csrf
    }),
  put: <T>(path: string, body?: unknown, csrf = true) =>
    request<T>(path, {
      method: 'PUT',
      body: JSON.stringify(body || {}),
      csrf
    }),
  delete: <T>(path: string, csrf = true) =>
    request<T>(path, {
      method: 'DELETE',
      csrf
    }),
  baseUrl: API_URL
};
