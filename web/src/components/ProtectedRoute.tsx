import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/lib/auth-store';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Redirect super admins to admin console when they try to access root
  if (user?.role === 'super_admin' && location.pathname === '/') {
    return <Navigate to="/super-admin" replace />;
  }

  // Redirect school admins to school admin console when they try to access root
  if (user?.role === 'school_admin' && location.pathname === '/') {
    return <Navigate to="/school-admin" replace />;
  }

  return <>{children}</>;
}
