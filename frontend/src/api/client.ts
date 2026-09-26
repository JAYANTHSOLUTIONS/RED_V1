import type { SuccessEnvelope, ErrorEnvelope } from './types';

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string = 'API_ERROR', status: number = 400) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  idempotencyKey?: string;
  skipAuth?: boolean;
}

let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

async function attemptTokenRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem('red_refresh_token');
  if (!refreshToken) {
    localStorage.removeItem('red_token');
    localStorage.removeItem('red_refresh_token');
    localStorage.removeItem('red_user');
    return null;
  }

  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      localStorage.removeItem('red_token');
      localStorage.removeItem('red_refresh_token');
      localStorage.removeItem('red_user');
      return null;
    }

    const envelope: SuccessEnvelope<{ access_token: string; refresh_token: string }> = await res.json();
    if (envelope.data?.access_token) {
      localStorage.setItem('red_token', envelope.data.access_token);
      if (envelope.data.refresh_token) {
        localStorage.setItem('red_refresh_token', envelope.data.refresh_token);
      }
      return envelope.data.access_token;
    }
  } catch {
    localStorage.removeItem('red_token');
    localStorage.removeItem('red_refresh_token');
    localStorage.removeItem('red_user');
  }
  return null;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { idempotencyKey, skipAuth = false, headers: customHeaders, ...fetchOptions } = options;

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const headers = new Headers(customHeaders);

  if (!headers.has('Content-Type') && !(fetchOptions.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (!skipAuth) {
    const token = localStorage.getItem('red_token');
    if (token && token !== 'demo-jwt-token' && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  if (idempotencyKey) {
    headers.set('Idempotency-Key', idempotencyKey);
  }

  let response: Response;
  try {
    response = await fetch(url, { ...fetchOptions, headers });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Network request failed';
    throw new ApiError(`Network connection error: ${msg}. Make sure backend is running.`, 'NETWORK_ERROR', 0);
  }

  // Handle 401 and attempt silent refresh
  if (response.status === 401 && !skipAuth && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    if (!isRefreshing) {
      isRefreshing = true;
      refreshPromise = attemptTokenRefresh().finally(() => {
        isRefreshing = false;
        refreshPromise = null;
      });
    }

    const newToken = await refreshPromise;
    if (newToken) {
      headers.set('Authorization', `Bearer ${newToken}`);
      response = await fetch(url, { ...fetchOptions, headers });
    } else {
      // Refresh failed, user must log in
      localStorage.removeItem('red_token');
      localStorage.removeItem('red_refresh_token');
      localStorage.removeItem('red_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
      throw new ApiError('Session expired. Please log in again.', 'UNAUTHORIZED', 401);
    }
  }

  if (!response.ok) {
    let errorMsg = `Request failed with status ${response.status}`;
    let errorCode = 'REQUEST_FAILED';

    try {
      const errJson = await response.json() as ErrorEnvelope;
      if (errJson?.error) {
        errorMsg = errJson.error.message || errorMsg;
        errorCode = errJson.error.code || errorCode;
      }
    } catch {
      // Non-json response
      const text = await response.text().catch(() => '');
      if (text) errorMsg = text;
    }

    throw new ApiError(errorMsg, errorCode, response.status);
  }

  // For 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  const envelope = await response.json() as SuccessEnvelope<T>;
  return envelope.data;
}

// Generate simple UUIDv4 for Idempotency-Key headers
export function generateIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
