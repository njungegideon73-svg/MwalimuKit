import { apiFetch } from '@/lib/api';
import type { User } from '@mwalimukit/types';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export async function login(email: string, password: string): Promise<TokenPair & { user: User }> {
  return apiFetch<TokenPair & { user: User }>('/auth/login', {
    method: 'POST',
    json: { email, password },
  });
}

export async function signup(data: {
  full_name: string;
  email: string;
  password: string;
  school_code: string;
}): Promise<TokenPair & { user: User }> {
  return apiFetch<TokenPair & { user: User }>('/auth/signup', {
    method: 'POST',
    json: data,
  });
}

export async function refreshToken(refreshToken: string): Promise<TokenPair> {
  return apiFetch<TokenPair>('/auth/refresh', {
    method: 'POST',
    json: { refresh_token: refreshToken },
  });
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<{ changed: boolean }> {
  return apiFetch<{ changed: boolean }>('/auth/change-password', {
    method: 'POST',
    json: { current_password: currentPassword, new_password: newPassword },
  });
}

export async function changeSchoolCode(currentPassword: string, newSchoolCode: string): Promise<{ changed: boolean; school_id: string }> {
  return apiFetch<{ changed: boolean; school_id: string }>('/auth/change-school-code', {
    method: 'POST',
    json: { current_password: currentPassword, new_school_code: newSchoolCode },
  });
}
