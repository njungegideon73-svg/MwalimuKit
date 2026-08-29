import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/lib/auth-store';
import toast from 'react-hot-toast';

export function useLogin() {
  const login = useAuthStore((s) => s.login);
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) => login(email, password),
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useSignup() {
  const signup = useAuthStore((s) => s.signup);
  return useMutation({
    mutationFn: (data: { full_name: string; email: string; password: string; school_code: string }) => signup(data),
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useLogout() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  return useMutation({
    mutationFn: async () => {
      await logout();
    },
    onSuccess: () => {
      navigate('/login');
    },
  });
}

export function useChangePassword() {
  const changePassword = useAuthStore((s) => s.changePassword);
  return useMutation({
    mutationFn: ({ current_password, new_password }: { current_password: string; new_password: string }) =>
      changePassword(current_password, new_password),
    onSuccess: () => toast.success('Password changed'),
    onError: (error: Error) => toast.error(error.message),
  });
}

export function useChangeSchoolCode() {
  const changeSchoolCode = useAuthStore((s) => s.changeSchoolCode);
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
