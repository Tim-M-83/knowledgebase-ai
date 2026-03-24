'use client';

import { useParams, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/toast';
import { api } from '@/lib/api';
import { DocumentDetail } from '@/lib/types';

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [departments, setDepartments] = useState<Array<{ id: number; name: string }>>([]);
  const [folders, setFolders] = useState<Array<{ id: number; name: string }>>([]);
  const [tags, setTags] = useState<Array<{ id: number; name: string }>>([]);
  const [selectedDepartment, setSelectedDepartment] = useState<string>('');
  const [selectedFolder, setSelectedFolder] = useState<string>('');
  const [selectedTags, setSelectedTags] = useState<number[]>([]);
  const [newDepartmentName, setNewDepartmentName] = useState('');
  const [newFolderName, setNewFolderName] = useState('');
  const [newTagName, setNewTagName] = useState('');
  const [addingDepartment, setAddingDepartment] = useState(false);
  const [addingFolder, setAddingFolder] = useState(false);
  const [addingTag, setAddingTag] = useState(false);
  const [savingMetadata, setSavingMetadata] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const { toast, Toast } = useToast();

  const loadDocument = async () => {
    if (!id) return;
    const detail = await api.get<DocumentDetail>(`/documents/${id}`);
    setDoc(detail);
    setSelectedDepartment(detail.department_id ? String(detail.department_id) : '');
    setSelectedFolder(detail.folder_id ? String(detail.folder_id) : '');
    setSelectedTags(detail.tag_ids || []);
  };

  useEffect(() => {
    if (!id) return;
    Promise.all([
      loadDocument(),
      api.get<Array<{ id: number; name: string }>>('/folders').then(setFolders),
      api.get<Array<{ id: number; name: string }>>('/departments').then(setDepartments),
      api.get<Array<{ id: number; name: string }>>('/tags').then(setTags)
    ]).catch(() => undefined);
  }, [id]);

  useEffect(() => {
    if (!doc || (doc.status !== 'uploaded' && doc.status !== 'processing')) return;
    const timer = window.setInterval(() => {
      loadDocument().catch(() => undefined);
    }, 7000);
    return () => window.clearInterval(timer);
  }, [doc?.id, doc?.status]);

  const onDelete = async () => {
    if (!doc) return;
    const confirmed = window.confirm(`Delete document "${doc.original_name}"? This cannot be undone.`);
    if (!confirmed) return;
    await api.delete(`/documents/${doc.id}`, true);
    router.push('/documents');
  };

  const toggleTag = (tagId: number) => {
    setSelectedTags((prev) => (prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]));
  };

  const saveMetadata = async () => {
    if (!doc) return;
    setSavingMetadata(true);
    setMessage(null);
    try {
      const updated = await api.put<DocumentDetail>(
        `/documents/${doc.id}/metadata`,
        {
          department_id: selectedDepartment ? Number(selectedDepartment) : null,
          folder_id: selectedFolder ? Number(selectedFolder) : null,
          tag_ids: selectedTags
        },
        true
      );
      setDoc(updated);
      setMessage('Metadata updated successfully.');
    } catch (error) {
      setMessage(`Update failed: ${(error as Error).message}`);
    } finally {
      setSavingMetadata(false);
    }
  };

  const addDepartment = async () => {
    const name = newDepartmentName.trim();
    if (!name) return;
    setAddingDepartment(true);
    setMessage(null);
    try {
      const created = await api.post<{ id: number; name: string }>('/departments', { name }, true);
      setDepartments((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedDepartment(String(created.id));
      setNewDepartmentName('');
      toast(`Department "${created.name}" added`);
    } catch (error) {
      setMessage(`Department creation failed: ${(error as Error).message}`);
    } finally {
      setAddingDepartment(false);
    }
  };

  const addFolder = async () => {
    const name = newFolderName.trim();
    if (!name) return;
    setAddingFolder(true);
    setMessage(null);
    try {
      const created = await api.post<{ id: number; name: string }>('/folders', { name }, true);
      setFolders((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedFolder(String(created.id));
      setNewFolderName('');
      toast(`Folder "${created.name}" added`);
    } catch (error) {
      setMessage(`Folder creation failed: ${(error as Error).message}`);
    } finally {
      setAddingFolder(false);
    }
  };

  const addTag = async () => {
    const name = newTagName.trim();
    if (!name) return;
    setAddingTag(true);
    setMessage(null);
    try {
      const created = await api.post<{ id: number; name: string }>('/tags', { name }, true);
      setTags((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSelectedTags((prev) => (prev.includes(created.id) ? prev : [...prev, created.id]));
      setNewTagName('');
      toast(`Tag "${created.name}" added`);
    } catch (error) {
      setMessage(`Tag creation failed: ${(error as Error).message}`);
    } finally {
      setAddingTag(false);
    }
  };

  const onIndex = async () => {
    if (!doc) return;
    setIndexing(true);
    setMessage(null);
    try {
      await api.post(`/documents/${doc.id}/index`, {}, true);
      toast('Indexing started');
      await loadDocument();
    } catch (error) {
      setMessage(`Indexing failed: ${(error as Error).message}`);
    } finally {
      setIndexing(false);
    }
  };

  const statusLabel = (status: DocumentDetail['status']) => {
    if (status === 'uploaded') return 'Queued for indexing';
    if (status === 'processing') return 'Indexing';
    if (status === 'ready') return 'Indexed';
    return 'Index failed';
  };

  if (!doc) return <Skeleton className='h-64' />;

  return (
    <div className='space-y-4'>
      <Card>
        <h1 className='text-xl font-semibold'>{doc.original_name}</h1>
        <div className='mt-3 flex flex-wrap items-center gap-2'>
          <Badge>{statusLabel(doc.status)}</Badge>
          <Badge>{doc.visibility}</Badge>
          <Badge>{doc.chunk_count} chunks</Badge>
        </div>
        <p className='mt-4 text-sm text-slate-600'>
          MIME: {doc.mime_type} | Size: {(doc.size / 1024).toFixed(1)} KB
        </p>
        <div className='mt-4'>
          <div className='flex flex-wrap gap-2'>
            <Button variant='secondary' onClick={onIndex} disabled={doc.status === 'processing' || indexing}>
              {doc.status === 'processing' || indexing ? 'Indexing...' : 'Index'}
            </Button>
            <Button variant='danger' onClick={onDelete}>
              Delete Document
            </Button>
          </div>
        </div>
        {doc.error_text ? (
          <p className='mt-3 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700'>{doc.error_text}</p>
        ) : null}
      </Card>

      <Card>
        <h2 className='text-lg font-semibold'>Folder, Tags and Department</h2>
        <div className='mt-4 grid gap-4'>
          <div>
            <label className='mb-2 block text-sm font-medium text-slate-700'>Folder</label>
            <Select value={selectedFolder} onChange={(e) => setSelectedFolder(e.target.value)}>
              <option value=''>No Folder</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.name}
                </option>
              ))}
            </Select>
            <div className='mt-2 flex gap-2'>
              <Input
                placeholder='New folder'
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
              />
              <Button
                type='button'
                variant='secondary'
                onClick={addFolder}
                disabled={!newFolderName.trim() || addingFolder}
              >
                {addingFolder ? 'Adding...' : 'Add'}
              </Button>
            </div>
          </div>

          <div>
            <label className='mb-2 block text-sm font-medium text-slate-700'>Department</label>
            <Select value={selectedDepartment} onChange={(e) => setSelectedDepartment(e.target.value)}>
              <option value=''>No Department</option>
              {departments.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </Select>
            <div className='mt-2 flex gap-2'>
              <Input
                placeholder='New department'
                value={newDepartmentName}
                onChange={(e) => setNewDepartmentName(e.target.value)}
              />
              <Button
                type='button'
                variant='secondary'
                onClick={addDepartment}
                disabled={!newDepartmentName.trim() || addingDepartment}
              >
                {addingDepartment ? 'Adding...' : 'Add'}
              </Button>
            </div>
          </div>

          <div>
            <label className='mb-2 block text-sm font-medium text-slate-700'>Tags</label>
            <div className='grid gap-2 sm:grid-cols-2'>
              {tags.map((tag) => (
                <label key={tag.id} className='flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2'>
                  <input
                    type='checkbox'
                    checked={selectedTags.includes(tag.id)}
                    onChange={() => toggleTag(tag.id)}
                  />
                  <span className='text-sm'>{tag.name}</span>
                </label>
              ))}
            </div>
            <div className='mt-2 flex gap-2'>
              <Input placeholder='New tag' value={newTagName} onChange={(e) => setNewTagName(e.target.value)} />
              <Button
                type='button'
                variant='secondary'
                onClick={addTag}
                disabled={!newTagName.trim() || addingTag}
              >
                {addingTag ? 'Adding...' : 'Add'}
              </Button>
            </div>
          </div>

          <div className='flex items-center gap-3'>
            <Button onClick={saveMetadata} disabled={savingMetadata}>
              {savingMetadata ? 'Saving...' : 'Save Metadata'}
            </Button>
            {message ? <p className='text-sm text-slate-600'>{message}</p> : null}
          </div>
        </div>
      </Card>
      <Toast />
    </div>
  );
}
