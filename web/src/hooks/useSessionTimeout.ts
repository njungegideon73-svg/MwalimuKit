import { useEffect, useRef, useState, useCallback } from 'react';

const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes
const WARNING_BEFORE_TIMEOUT = 2 * 60_1000; // 2 minutes before logout

interface UseSessionTimeoutOptions {
  onTimeout?: () => void;
  onWarning?: () => void;
}

export function useSessionTimeout(options: UseSessionTimeoutOptions = {}) {
  const { onTimeout, onWarning } = options;
  const [isWarning, setIsWarning] = useState(false);
  const [countdown, setCountdown] = useState(120); // 2 minutes countdown
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdownIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastActivityRef = useRef<number>(Date.now());

  const clearTimers = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
    timerRef.current = null;
    warningTimerRef.current = null;
    countdownIntervalRef.current = null;
  }, []);

  const resetTimer = useCallback(() => {
    clearTimers();
    lastActivityRef.current = Date.now();
    setIsWarning(false);
    setCountdown(120);

    // Set warning timer
    warningTimerRef.current = setTimeout(() => {
      setIsWarning(true);
      onWarning?.();

      // Start countdown
      countdownIntervalRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownIntervalRef.current as any);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      // Set logout timer
      timerRef.current = setTimeout(() => {
        clearTimers();
        onTimeout?.();
      }, WARNING_BEFORE_TIMEOUT);
    }, INACTIVITY_TIMEOUT - WARNING_BEFORE_TIMEOUT);
  }, [clearTimers, onTimeout, onWarning]);

  const dismissWarning = useCallback(() => {
    clearTimers();
    setIsWarning(false);
    setCountdown(120);
    resetTimer();
  }, [clearTimers, resetTimer]);

  // Track user activity
  useEffect(() => {
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart', 'mousedown'];
    const handleActivity = () => {
      const now = Date.now();
      if (now - lastActivityRef.current > 60_000) {
        resetTimer();
      }
    };

    events.forEach((event) => window.addEventListener(event, handleActivity, { passive: true }));
    resetTimer();

    return () => {
      events.forEach((event) => window.removeEventListener(event, handleActivity));
      clearTimers();
    };
  }, [resetTimer, clearTimers]);

  // Clear tokens on browser/tab close
  useEffect(() => {
    const handleBeforeUnload = () => {
      try {
        localStorage.removeItem('mk_auth');
      } catch {
        // Ignore storage errors
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);

  return {
    isWarning,
    countdown,
    dismissWarning,
    resetTimer,
  };
}
