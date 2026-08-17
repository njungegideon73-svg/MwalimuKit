import { create } from 'zustand';
import type { User } from '@mwalimukit/types';
import { apiFetch, saveTokens, clearTokens, getTokens } from '@/lib/api';
import { db } from '@/lib/db';
import { invalidateCurriculumCache } from '@/lib/curriculum';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (data: {
    full_name: string;
    email: string;
    password: string;
    school_code: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email, password) => {
    const res = await apiFetch<{ access_token: string; refresh_token: string; user: User }>(
      '/auth/login',
      { method: 'POST', json: { email, password } },
    );
    saveTokens(res.access_token, res.refresh_token);
    set({ user: res.user, isAuthenticated: true });
  },

  signup: async (data) => {
    const res = await apiFetch<{ access_token: string; refresh_token: string; user: User }>(
      '/auth/signup',
      { method: 'POST', json: data },
    );
    saveTokens(res.access_token, res.refresh_token);
    set({ user: res.user, isAuthenticated: true });
  },

  logout: async () => {
    clearTokens();
    invalidateCurriculumCache();
    await db.delete();
    set({ user: null, isAuthenticated: false });
  },

  hydrate: async () => {
    const { access, refresh } = getTokens();
    if (!access && !refresh) {
      set({ isLoading: false });
      return;
    }
    try {
      const user = await apiFetch<{ id: string; school_id: string; email: string; full_name: string; role: string }>(
        '/schools/me',
      );
      set({ user: user as User, isAuthenticated: true, isLoading: false });
    } catch {
      clearTokens();
      set({ isLoading: false });
    }
  },
}));
