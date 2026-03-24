'use client';

import { useEffect, useState } from 'react';

export function useToast() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(null), 2500);
    return () => clearTimeout(timer);
  }, [message]);

  const Toast = () =>
    message ? (
      <div className='fixed bottom-4 right-4 rounded-2xl bg-ink px-4 py-2 text-sm text-white shadow-soft'>
        {message}
      </div>
    ) : null;

  return { toast: setMessage, Toast };
}
