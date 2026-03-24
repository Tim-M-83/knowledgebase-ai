'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Table } from '@/components/ui/table';
import { api } from '@/lib/api';

type UserRow = { id: number; email: string; role: 'admin' | 'editor' | 'viewer'; department_id?: number | null };

export default function AdminUsersPage() {
  const [rows, setRows] = useState<UserRow[]>([]);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'admin' | 'editor' | 'viewer'>('viewer');

  const load = () => api.get<UserRow[]>('/users').then(setRows);

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    await api.post('/users', { email, password, role }, true);
    setEmail('');
    setPassword('');
    setRole('viewer');
    await load();
  };

  const remove = async (id: number) => {
    await api.delete(`/users/${id}`, true);
    await load();
  };

  return (
    <div className='space-y-4'>
      <Card>
        <h2 className='mb-3 text-sm font-semibold'>Taxonomy Management</h2>
        <div className='flex flex-wrap gap-2'>
          <Link
            href='/admin/tags'
            className='rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50'
          >
            Manage Tags
          </Link>
          <Link
            href='/admin/departments'
            className='rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50'
          >
            Manage Departments
          </Link>
          <Link
            href='/admin/folders'
            className='rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:bg-slate-50'
          >
            Manage Folders
          </Link>
        </div>
      </Card>
      <Card>
        <h2 className='mb-3 text-sm font-semibold'>Create User</h2>
        <form onSubmit={create} className='grid gap-3 md:grid-cols-4'>
          <Input placeholder='Email' type='email' value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input
            placeholder='Password'
            type='password'
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Select value={role} onChange={(e) => setRole(e.target.value as any)}>
            <option value='viewer'>Viewer</option>
            <option value='editor'>Editor</option>
            <option value='admin'>Admin</option>
          </Select>
          <Button type='submit'>Create</Button>
        </form>
      </Card>

      <Card>
        <h2 className='mb-3 text-sm font-semibold'>Users</h2>
        <Table>
          <thead>
            <tr className='text-left text-xs uppercase text-slate-500'>
              <th className='pb-2'>Email</th>
              <th className='pb-2'>Role</th>
              <th className='pb-2'>Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((user) => (
              <tr key={user.id} className='border-t border-slate-100'>
                <td className='py-3'>{user.email}</td>
                <td className='py-3'>{user.role}</td>
                <td className='py-3'>
                  <Button variant='danger' onClick={() => remove(user.id)}>
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  );
}
