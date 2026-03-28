'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { api } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const [loggingOut, setLoggingOut] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [emailHelperEnabled, setEmailHelperEnabled] = useState(false);
  const [currentRole, setCurrentRole] = useState<'admin' | 'editor' | 'viewer' | null>(null);
  const [mustChangeCredentials, setMustChangeCredentials] = useState(false);

  useEffect(() => {
    if (pathname === '/login') {
      return;
    }
    getCurrentUser()
      .then((user) => {
        setEmailHelperEnabled(Boolean(user?.email_helper_enabled));
        setCurrentRole(user?.role ?? null);
        setMustChangeCredentials(Boolean(user?.must_change_credentials));
        if (!user) {
          return;
        }
        if (user.must_change_credentials && pathname !== '/settings') {
          router.replace('/settings');
          return;
        }
        const isInactiveSubscription = user.license_enabled && !user.license_active;
        const isInactiveRoute = pathname.startsWith('/subscription-inactive');
        const isAdminSettingsRoute = user.role === 'admin' && pathname.startsWith('/settings');
        if (isInactiveSubscription && !isInactiveRoute && !isAdminSettingsRoute) {
          router.replace('/subscription-inactive');
        }
      })
      .catch(() => {
        setEmailHelperEnabled(false);
        setCurrentRole(null);
        setMustChangeCredentials(false);
      });
  }, [pathname, router]);

  const navItems = useMemo(() => {
    if (mustChangeCredentials) {
      return [{ href: '/settings', label: 'Settings' }];
    }
    const base = [
      { href: '/dashboard', label: 'Dashboard' },
      { href: '/chat', label: 'Chat' },
      { href: '/ai-document-summarizer', label: 'AI Document Summarizer' },
      { href: '/personal-notes', label: 'Personal Notes' },
    ];
    if (emailHelperEnabled) {
      base.push({ href: '/email-helper', label: 'Email Helper' });
    }
    base.push({ href: '/documents', label: 'Documents' });
    base.push({ href: '/admin/users', label: 'Admin' });
    base.push({ href: '/settings', label: 'Settings' });
    return base;
  }, [emailHelperEnabled, currentRole, mustChangeCredentials]);

  if (pathname === '/login') {
    return null;
  }

  const onLogout = async () => {
    setLoggingOut(true);
    setErrorText(null);
    try {
      await api.post('/auth/logout', {}, false);
      router.replace('/login');
      router.refresh();
    } catch (error) {
      setErrorText(`Logout failed: ${(error as Error).message}`);
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <header className='border-b border-slate-200 bg-white/90 backdrop-blur'>
      <div className='mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-3'>
        <Link href='/dashboard' aria-label='KnowledgeBase AI home' className='inline-flex shrink-0 items-center'>
          <Image
            src='/knowledgebase-ai-logo.png'
            alt='KnowledgeBase AI'
            width={149}
            height={52}
            priority
            className='h-[52px] w-auto'
          />
        </Link>
        <div className='flex items-center gap-2'>
          <nav className='flex gap-2'>
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className='rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-slate-100 hover:text-ink'
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <button
            type='button'
            onClick={onLogout}
            disabled={loggingOut}
            className='rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60'
          >
            {loggingOut ? 'Logging out...' : 'Logout'}
          </button>
        </div>
      </div>
      {errorText ? (
        <div className='mx-auto max-w-7xl px-4 pb-2'>
          <p className='text-sm text-red-700'>{errorText}</p>
        </div>
      ) : null}
    </header>
  );
}
