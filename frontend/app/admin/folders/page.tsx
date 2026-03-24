'use client';

import { FormEvent, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Table } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { api } from '@/lib/api';

type Folder = { id: number; name: string };

export default function AdminFoldersPage() {
  const [rows, setRows] = useState<Folder[]>([]);
  const [name, setName] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const { toast, Toast } = useToast();

  const load = () => api.get<Folder[]>('/folders').then(setRows);

  useEffect(() => {
    load().catch((error) => toast(`Loading folders failed: ${(error as Error).message}`));
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      await api.post('/folders', { name: trimmed }, true);
      setName('');
      toast(`Folder "${trimmed}" added`);
      await load();
    } catch (error) {
      toast(`Add failed: ${(error as Error).message}`);
    }
  };

  const remove = async (folder: Folder) => {
    const confirmed = window.confirm(
      `Delete folder "${folder.name}"? Assigned documents will be set to no folder.`
    );
    if (!confirmed) return;

    try {
      await api.delete(`/folders/${folder.id}`, true);
      toast(`Folder "${folder.name}" deleted`);
      await load();
    } catch (error) {
      toast(`Delete failed: ${(error as Error).message}`);
    }
  };

  const startEdit = (folder: Folder) => {
    setEditingId(folder.id);
    setEditingName(folder.name);
  };

  const saveEdit = async (id: number) => {
    if (!editingName.trim()) return;
    try {
      await api.put(`/folders/${id}`, { name: editingName.trim() }, true);
      setEditingId(null);
      setEditingName('');
      toast('Folder updated');
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
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder='Folder name' />
          <Button type='submit'>Add Folder</Button>
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
            {rows.map((folder) => (
              <tr key={folder.id} className='border-t border-slate-100'>
                <td className='py-2'>
                  {editingId === folder.id ? (
                    <Input value={editingName} onChange={(e) => setEditingName(e.target.value)} />
                  ) : (
                    folder.name
                  )}
                </td>
                <td className='py-2 text-right'>
                  <div className='flex justify-end gap-2'>
                    {editingId === folder.id ? (
                      <>
                        <Button variant='secondary' onClick={cancelEdit} type='button'>
                          Cancel
                        </Button>
                        <Button onClick={() => saveEdit(folder.id)} type='button'>
                          Save
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button variant='secondary' onClick={() => startEdit(folder)} type='button'>
                          Edit
                        </Button>
                        <Button variant='danger' onClick={() => remove(folder)} type='button'>
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
