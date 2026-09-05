/**
 * API client with automatic token refresh.
 */
export const API_BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
  : '/api/v1';

interface FetchOptions extends RequestInit {
  json?: unknown;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function getTokens(): { access: string | null; refresh: string | null } {
  try {
    const raw = localStorage.getItem('mk_auth');
    if (!raw) return { access: null, refresh: null };
    const data = JSON.parse(raw);
    return { access: data?.access_token ?? null, refresh: data?.refresh_token ?? null };
  } catch {
    return { access: null, refresh: null };
  }
}

function saveTokens(access: string, refresh: string) {
  localStorage.setItem('mk_auth', JSON.stringify({ access_token: access, refresh_token: refresh }));
}

function clearTokens() {
  localStorage.removeItem('mk_auth');
}

async function tryRefresh(): Promise<boolean> {
  const { refresh } = getTokens();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    saveTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const { json, ...init } = opts;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  };

  const { access } = getTokens();
  if (access) {
    headers['Authorization'] = `Bearer ${access}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    body: json ? JSON.stringify(json) : init.body,
  });

  if (res.status === 401 && access) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      const { access: newAccess } = getTokens();
      if (newAccess) {
        headers['Authorization'] = `Bearer ${newAccess}`;
        const retryRes = await fetch(`${API_BASE}${path}`, {
          ...init,
          headers,
          body: json ? JSON.stringify(json) : init.body,
        });
        if (!retryRes.ok) {
          throw new ApiError(retryRes.status, await retryRes.text());
        }
        return retryRes.json() as Promise<T>;
      }
    }
    clearTokens();
    window.location.href = '/login';
    throw new ApiError(401, 'Session expired');
  }

  if (!res.ok) {
    let text = await res.text();
    try {
      const json = JSON.parse(text);
      if (typeof json.detail === 'string') {
        text = json.detail;
      }
    } catch {
      // Not JSON — keep raw text.
    }
    throw new ApiError(res.status, text);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

/**
 * Revoke the refresh token server-side. Best-effort: local tokens are
 * cleared regardless of network outcome.
 */
async function logoutApi(): Promise<void> {
  const { refresh } = getTokens();
  clearTokens();
  if (!refresh) return;
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
  } catch {
    // offline / server unreachable — local logout already happened
  }
}

export { ApiError, clearTokens, saveTokens, getTokens, logoutApi };
