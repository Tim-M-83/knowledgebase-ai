'use client';

import { FormEvent, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Table } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { api } from '@/lib/api';

type Tag = { id: number; name: string };

export default function AdminTagsPage() {
  const [rows, setRows] = useState<Tag[]>([]);
  const [name, setName] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingName, setEditingName] = useState('');
  const { toast, Toast } = useToast();

  const load = () => api.get<Tag[]>('/tags').then(setRows);

  useEffect(() => {
    load().catch((error) => toast(`Loading tags failed: ${(error as Error).message}`));
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      await api.post('/tags', { name: trimmed }, true);
      setName('');
      toast(`Tag "${trimmed}" added`);
      await load();
    } catch (error) {
      toast(`Add failed: ${(error as Error).message}`);
    }
  };

  const remove = async (tag: Tag) => {
    const confirmed = window.confirm(
      `Delete tag "${tag.name}"? It will be removed from all linked documents.`
    );
    if (!confirmed) return;

    try {
      await api.delete(`/tags/${tag.id}`, true);
      toast(`Tag "${tag.name}" deleted`);
      await load();
    } catch (error) {
      toast(`Delete failed: ${(error as Error).message}`);
    }
  };

  const startEdit = (tag: Tag) => {
    setEditingId(tag.id);
    setEditingName(tag.name);
  };

  const saveEdit = async (id: number) => {
    if (!editingName.trim()) return;
    try {
      await api.put(`/tags/${id}`, { name: editingName.trim() }, true);
      setEditingId(null);
      setEditingName('');
      toast('Tag updated');
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
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder='Tag name' />
          <Button type='submit'>Add Tag</Button>
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
            {rows.map((tag) => (
              <tr key={tag.id} className='border-t border-slate-100'>
                <td className='py-2'>
                  {editingId === tag.id ? (
                    <Input value={editingName} onChange={(e) => setEditingName(e.target.value)} />
                  ) : (
                    tag.name
                  )}
                </td>
                <td className='py-2 text-right'>
                  <div className='flex justify-end gap-2'>
                    {editingId === tag.id ? (
                      <>
                        <Button variant='secondary' onClick={cancelEdit} type='button'>
                          Cancel
                        </Button>
                        <Button onClick={() => saveEdit(tag.id)} type='button'>
                          Save
                        </Button>
                      </>
                    ) : (
                      <>
                        <Button variant='secondary' onClick={() => startEdit(tag)} type='button'>
                          Edit
                        </Button>
                        <Button variant='danger' onClick={() => remove(tag)} type='button'>
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
