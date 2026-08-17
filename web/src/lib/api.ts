/**
 * API client with automatic token refresh.
 */
const API_BASE = '/api/v1';

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
    const text = await res.text();
    throw new ApiError(res.status, text);
  }

  return res.json() as Promise<T>;
}

export { ApiError, clearTokens, saveTokens, getTokens };
