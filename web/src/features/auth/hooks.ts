import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { login, signup, changePassword, changeSchoolCode } from '@/features/auth/api';
import { saveTokens, clearTokens } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import toast from 'react-hot-toast';

export function useLogin() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => login(email, password),
    onSuccess: (data) => {
      saveTokens(data.access_token, data.refresh_token);
      useAuthStore.getState().setUser(data.user);
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useSignup() {
  return useMutation({
    mutationFn: (data: { full_name: string; email: string; password: string; school_code: string }) => signup(data),
    onSuccess: (data) => {
      saveTokens(data.access_token, data.refresh_token);
      useAuthStore.getState().setUser(data.user);
    },
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useLogout() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: async () => {
      clearTokens();
      await useAuthStore.getState().hydrate();
    },
    onSuccess: () => {
      navigate('/login');
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: ({ current_password, new_password }: { current_password: string; new_password: string }) =>
      changePassword(current_password, new_password),
    onSuccess: () => toast.success('Password changed'),
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useChangeSchoolCode() {
  return useMutation({
    mutationFn: ({ current_password, new_school_code }: { current_password: string; new_school_code: string }) =>
      changeSchoolCode(current_password, new_school_code),
    onSuccess: () => toast.success('School code changed'),
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useUserPermissions() {
  const user = useAuthStore((s) => s.user);
  const role = user?.role ?? null;
  return {
    role,
    isTeacher: role === 'teacher',
    isSchoolAdmin: role === 'school_admin' || role === 'super_admin',
    isSuperAdmin: role === 'super_admin',
  };
}
