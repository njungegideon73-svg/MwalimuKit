import { create } from 'zustand';
import type { User } from '@mwalimukit/types';
import { apiFetch, saveTokens, clearTokens, getTokens, logoutApi } from '@/lib/api';
import { db } from '@/lib/db';
import { invalidateCurriculumCache } from '@/lib/curriculum';
import { setSentryUser } from '@/lib/sentry';

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
  getRedirectPath: () => string;
  setUser: (user: User | null) => void;
  changePassword: (currentPassword: string, newPassword: string) => Promise<{ changed: boolean }>;
  changeSchoolCode: (currentPassword: string, newSchoolCode: string) => Promise<{ changed: boolean; school_id: string }>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email, password) => {
    const res = await apiFetch<{ access_token: string; refresh_token: string; user: User }>(
      '/auth/login',
      { method: 'POST', json: { email, password } },
    );
    saveTokens(res.access_token, res.refresh_token);
    set({ user: res.user, isAuthenticated: true, isLoading: false });
    setSentryUser(res.user);
  },

  signup: async (data) => {
    const res = await apiFetch<{ access_token: string; refresh_token: string; user: User }>(
      '/auth/signup',
      { method: 'POST', json: data },
    );
    saveTokens(res.access_token, res.refresh_token);
    set({ user: res.user, isAuthenticated: true, isLoading: false });
    setSentryUser(res.user);
  },

  logout: async () => {
    await logoutApi(); // revoke refresh token server-side (best-effort)
    clearTokens();
    invalidateCurriculumCache();
    await db.delete();
    set({ user: null, isAuthenticated: false });
    setSentryUser(null);
  },

  hydrate: async () => {
    const { user } = get();
    if (user) {
      set({ isLoading: false });
      return;
    }
    const { access, refresh } = getTokens();
    if (!access && !refresh) {
      set({ isLoading: false });
      return;
    }
    try {
      const data = await apiFetch<{ id: string; school_id: string; email: string; full_name: string; role: string }>(
        '/schools/me',
      );
      const typedUser = data as User;
      set({ user: typedUser, isAuthenticated: true, isLoading: false });
      setSentryUser(typedUser);
    } catch {
      clearTokens();
      set({ isLoading: false });
    }
  },

  getRedirectPath: () => {
    const { user } = get();
    if (!user) return '/';
    
    switch (user.role) {
      case 'super_admin':
        return '/super-admin';
      case 'school_admin':
        return '/school-admin';
      default:
        return '/';
    }
  },

  setUser: (user: User | null) => {
    set({ user, isAuthenticated: !!user, isLoading: false });
  },

  changePassword: async (currentPassword, newPassword) => {
    const res = await apiFetch<{ changed: boolean }>('/auth/change-password', {
      method: 'POST',
      json: { current_password: currentPassword, new_password: newPassword },
    });
    return res;
  },

  changeSchoolCode: async (currentPassword, newSchoolCode) => {
    const res = await apiFetch<{ changed: boolean; school_id: string }>('/auth/change-school-code', {
      method: 'POST',
      json: { current_password: currentPassword, new_school_code: newSchoolCode },
    });
    return res;
  },
}));
