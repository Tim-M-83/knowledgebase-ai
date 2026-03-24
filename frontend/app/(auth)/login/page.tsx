'use client';

import { FormEvent, useState } from 'react';

import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { User } from '@/lib/types';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await api.post<User>('/auth/login', { email, password });
      window.location.assign(user.must_change_credentials ? '/settings' : '/dashboard');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className='mx-auto mt-16 max-w-md'>
      <Card>
        <h1 className='mb-4 text-xl font-semibold'>Sign in</h1>
        <form onSubmit={onSubmit} className='space-y-3'>
          <Input placeholder='Email' type='text' value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input
            placeholder='Password'
            type='password'
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error ? <p className='text-sm text-red-600'>{error}</p> : null}
          <Button disabled={loading} className='w-full'>
            {loading ? 'Signing in...' : 'Login'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
