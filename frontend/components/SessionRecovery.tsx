'use client';

import { useEffect, useRef } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { api, AUTH_UNAUTHORIZED_EVENT } from '@/lib/api';

export function SessionRecovery() {
  const pathname = usePathname();
  const router = useRouter();
  const recoveryInProgress = useRef(false);

  useEffect(() => {
    if (pathname === '/login') {
      recoveryInProgress.current = false;
    }
  }, [pathname]);

  useEffect(() => {
    const handleUnauthorized = async () => {
      if (recoveryInProgress.current) {
        return;
      }
      recoveryInProgress.current = true;

      try {
        await fetch(`${api.baseUrl}/auth/logout`, {
          method: 'POST',
          headers: { Accept: 'application/json' },
          credentials: 'include',
        });
      } catch {
        // Best-effort only. Redirecting to /login is the important part.
      }

      if (pathname !== '/login') {
        window.location.replace('/login');
        return;
      }

      router.refresh();
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, [pathname, router]);

  return null;
}
