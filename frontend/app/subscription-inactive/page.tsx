'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { api } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import { LicenseStatus, Role } from '@/lib/types';

export default function SubscriptionInactivePage() {
  const router = useRouter();
  const [role, setRole] = useState<Role | null>(null);
  const [license, setLicense] = useState<LicenseStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [me, status] = await Promise.all([
          getCurrentUser(),
          api.get<LicenseStatus>('/license/status'),
        ]);
        setRole(me?.role ?? null);
        setLicense(status);
        if (status.license_active) {
          router.replace('/dashboard');
        }
      } catch {
        router.replace('/login');
      } finally {
        setLoading(false);
      }
    };
    load().catch(() => undefined);
  }, [router]);

  return (
    <div className='mx-auto max-w-2xl'>
      <Card>
        <h1 className='text-xl font-semibold text-slate-900'>License Inactive</h1>
        <p className='mt-2 text-sm text-slate-600'>
          This workspace is currently blocked because the local installation does not have an active validated license.
          Activate or validate the current license to re-enable protected application features.
        </p>
        <div className='mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950'>
          <p className='font-semibold'>Start your 7-day free trial</p>
          <p className='mt-1'>
            Every new workspace can start with a 7-day free trial. You can begin the trial from License Settings before
            purchasing a full subscription.
          </p>
        </div>
        {!loading && license ? (
          <div className='mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600'>
            <p>Status: {license.license_status || 'inactive'}</p>
            {license.current_period_end ? <p>Current period end: {license.current_period_end}</p> : null}
            {license.last_validated_at ? <p>Last validation: {license.last_validated_at}</p> : null}
            {license.grace_until ? <p>Grace until: {license.grace_until}</p> : null}
            {license.last_error ? <p className='text-red-700'>Last error: {license.last_error}</p> : null}
          </div>
        ) : null}
        {role === 'admin' ? (
          <div className='mt-4 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700'>
            <p className='font-semibold text-slate-900'>How to start the trial</p>
            <ol className='mt-2 list-decimal space-y-1 pl-5'>
              <li>Click <span className='font-medium'>Open License Settings</span>.</li>
              <li>Click <span className='font-medium'>Buy / Renew Subscription</span>.</li>
              <li>Complete checkout on the hosted license page to start the 7-day free trial.</li>
              <li>Return here and finish the activation or validation flow if the installation still needs recovery.</li>
              <li>If the workspace has already used all activation slots, click <span className='font-medium'>Reset All Activations</span> in License Settings before activating this installation again.</li>
            </ol>
          </div>
        ) : null}
        <div className='mt-4 flex flex-wrap gap-2'>
          {role === 'admin' ? (
            <Button onClick={() => router.push('/settings')}>Open License Settings</Button>
          ) : (
            <p className='text-sm text-slate-600'>
              Contact your workspace administrator. They can open License Settings and click Buy / Renew Subscription
              to start the 7-day free trial and reactivate this workspace.
            </p>
          )}
          <Button variant='secondary' onClick={() => router.push('/dashboard')}>
            Retry Access
          </Button>
        </div>
      </Card>
    </div>
  );
}
