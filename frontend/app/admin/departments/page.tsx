'use client';

import { FormEvent, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Table } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { api } from '@/lib/api';

type Department = { id: number; name: string };

export default function AdminDepartmentsPage() {
  const [rows, setRows] = useState<Department[]>([]);
  const [name, setName] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const { toast, Toast } = useToast();

  const load = () => api.get<Department[]>('/departments').then(setRows);

  useEffect(() => {
    load().catch((error) => toast(`Loading departments failed: ${(error as Error).message}`));
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      await api.post('/departments', { name: trimmed }, true);
      setName('');
      toast(`Department "${trimmed}" added`);
      await load();
    } catch (error) {
      toast(`Add failed: ${(error as Error).message}`);
    }
  };

  const remove = async (department: Department) => {
    const confirmed = window.confirm(
      `Delete department "${department.name}"? Assigned users and documents will be set to no department.`
    );
    if (!confirmed) return;

    try {
      await api.delete(`/departments/${department.id}`, true);
      toast(`Department "${department.name}" deleted`);
      await load();
    } catch (error) {
      toast(`Delete failed: ${(error as Error).message}`);
    }
  };

  const startEdit = (department: Department) => {
    setEditingId(department.id);
    setEditingName(department.name);
  };

  const saveEdit = async (id: number) => {
    if (!editingName.trim()) return;
    try {
      await api.put(`/departments/${id}`, { name: editingName.trim() }, true);
      setEditingId(null);
      setEditingName('');
      toast('Department updated');
      await load();
    } catch (error) {
      toast(`Update failed: ${(error as Error).message}`);
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditingName('');
  };

  return (
    <div className='space-y-4'>
      <Card>
        <form onSubmit={create} className='flex gap-3'>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder='Department name' />
          <Button type='submit'>Add Department</Button>
        </form>
      </Card>
      <Card>
        <Table>
          <thead>
            <tr className='text-left text-xs uppercase text-slate-500'>
              <th className='pb-2'>Name</th>
              <th className='pb-2 text-right'>Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((department) => (
              <tr key={department.id} className='border-t border-slate-100'>
                <td className='py-2'>
                  {editingId === department.id ? (
                    <Input value={editingName} onChange={(e) => setEditingName(e.target.value)} />
                  ) : (
                    department.name
                  )}
                </td>
                <td className='py-2 text-right'>
                  <div className='flex justify-end gap-2'>
                    {editingId === department.id ? (
                      <>
                        <Button variant='secondary' onClick={cancelEdit} type='button'>
                          Cancel
                        </Button>
                        <Button onClick={() => saveEdit(department.id)} type='button'>
                          Save
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button variant='secondary' onClick={() => startEdit(department)} type='button'>
                          Edit
                        </Button>
                        <Button variant='danger' onClick={() => remove(department)} type='button'>
                          Delete
                        </Button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      <Toast />
    </div>
  );
}
