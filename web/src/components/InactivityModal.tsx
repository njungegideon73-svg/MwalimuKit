import { useState, useEffect } from 'react';
import { useAuthStore } from '@/lib/auth-store';
import { useSessionTimeout } from '@/hooks/useSessionTimeout';

export function InactivityModal() {
  const [countdown, setCountdown] = useState(120); // 2 minutes
  const logout = useAuthStore((s) => s.logout);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { resetTimer } = useSessionTimeout();

  useEffect(() => {
    if (!isAuthenticated) return;

    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const handleStayLoggedIn = () => {
    setCountdown(120);
    resetTimer();
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = '/login';
  };

  if (!isAuthenticated || countdown >= 120) return null;

  const minutes = Math.floor(countdown / 60);
  const seconds = countdown % 60;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl p-6 max-w-md w-full mx-4">
        <h2 className="text-xl font-bold text-gray-900 mb-2">Session Timeout Warning</h2>
        <p className="text-gray-600 mb-4">
          You have been inactive for 30 minutes. For your security, you will be automatically logged out in{' '}
          <span className="font-bold text-red-600">{minutes}:{seconds.toString().padStart(2, '0')}</span>.
        </p>
        <div className="flex gap-3">
          <button onClick={handleStayLoggedIn} className="btn-primary flex-1">
            Stay Logged In
          </button>
          <button onClick={handleLogout} className="btn-secondary flex-1">
            Log Out Now
          </button>
        </div>
      </div>
    </div>
  );
}
