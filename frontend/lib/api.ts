import { getCookie } from '@/lib/utils';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const AUTH_UNAUTHORIZED_EVENT = 'kb-auth-unauthorized';

export class UnauthorizedError extends Error {
  status = 401;

  constructor(message = 'Unauthorized') {
    super(message);
    this.name = 'UnauthorizedError';
  }
}

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
    let detail = raw || `Request failed: ${response.status}`;

    try {
      const parsed = JSON.parse(raw);
      detail = typeof parsed?.detail === 'string' ? parsed.detail : detail;
    } catch {
      // Fall back to the raw response text below.
    }

    if (response.status === 401) {
      if (typeof window !== 'undefined' && path !== '/auth/login') {
        window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
      }
      throw new UnauthorizedError(detail);
    }

    throw new Error(detail);
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
