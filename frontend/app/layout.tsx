import type { Metadata } from 'next';

import './globals.css';
import { AppHeader } from '@/components/AppHeader';
import { SessionRecovery } from '@/components/SessionRecovery';

export const metadata: Metadata = {
  title: 'KnowledgeBase AI',
  description: 'Internal knowledge base with AI instant answers',
  icons: {
    icon: '/favicon.svg',
    shortcut: '/favicon.svg',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='en'>
      <body>
        <div className='min-h-screen'>
          <SessionRecovery />
          <AppHeader />
          <main className='mx-auto max-w-7xl px-4 py-6'>{children}</main>
        </div>
      </body>
    </html>
  );
}
