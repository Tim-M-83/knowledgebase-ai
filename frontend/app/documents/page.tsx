'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { UploadDialog } from '@/components/UploadDialog';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Table } from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { api } from '@/lib/api';
import { DocumentItem } from '@/lib/types';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [departments, setDepartments] = useState<Array<{ id: number; name: string }>>([]);
  const [folders, setFolders] = useState<Array<{ id: number; name: string }>>([]);
  const [tags, setTags] = useState<Array<{ id: number; name: string }>>([]);
  const [folderFilter, setFolderFilter] = useState('');
  const [indexingIds, setIndexingIds] = useState<number[]>([]);
  const { toast, Toast } = useToast();

  const load = async () => {
    const [docs, deps, flds, tgs] = await Promise.all([
      api.get<DocumentItem[]>('/documents'),
      api.get<Array<{ id: number; name: string }>>('/departments'),
      api.get<Array<{ id: number; name: string }>>('/folders'),
      api.get<Array<{ id: number; name: string }>>('/tags')
    ]);
    setDocuments(docs);
    setDepartments(deps);
    setFolders(flds);
    setTags(tgs);
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!documents.some((doc) => doc.status === 'uploaded' || doc.status === 'processing')) return;
    const timer = window.setInterval(() => {
      load().catch(() => undefined);
    }, 7000);
    return () => window.clearInterval(timer);
  }, [documents]);

  const onUpload = async (formData: FormData) => {
    await api.post('/documents/upload', formData, true);
    toast('Upload started');
    await load();
  };

  const onCreateTag = async (name: string) => {
    const created = await api.post<{ id: number; name: string }>('/tags', { name }, true);
    setTags((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
    toast(`Tag "${created.name}" added`);
    return created;
  };

  const onCreateDepartment = async (name: string) => {
    const created = await api.post<{ id: number; name: string }>('/departments', { name }, true);
    setDepartments((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
    toast(`Department "${created.name}" added`);
    return created;
  };

  const onCreateFolder = async (name: string) => {
    const created = await api.post<{ id: number; name: string }>('/folders', { name }, true);
    setFolders((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
    toast(`Folder "${created.name}" added`);
    return created;
  };

  const onDelete = async (id: number, name: string) => {
    const confirmed = window.confirm(`Delete document "${name}"? This cannot be undone.`);
    if (!confirmed) return;
    try {
      await api.delete(`/documents/${id}`, true);
      toast('Document deleted');
      await load();
    } catch (error) {
      toast(`Delete failed: ${(error as Error).message}`);
    }
  };

  const onIndex = async (id: number) => {
    setIndexingIds((prev) => [...prev, id]);
    try {
      await api.post(`/documents/${id}/index`, {}, true);
      toast('Indexing started');
      await load();
    } catch (error) {
      toast(`Indexing failed: ${(error as Error).message}`);
    } finally {
      setIndexingIds((prev) => prev.filter((item) => item !== id));
    }
  };

  const statusLabel = (status: DocumentItem['status']) => {
    if (status === 'uploaded') return 'Queued for indexing';
    if (status === 'processing') return 'Indexing';
    if (status === 'ready') return 'Indexed';
    return 'Index failed';
  };

  const filteredDocuments = folderFilter
    ? documents.filter((doc) => String(doc.folder_id || '') === folderFilter)
    : documents;

  const folderNameById = new Map(folders.map((folder) => [folder.id, folder.name]));

  return (
    <div className='space-y-4'>
      <UploadDialog
        onUpload={onUpload}
        onCreateTag={onCreateTag}
        onCreateDepartment={onCreateDepartment}
        onCreateFolder={onCreateFolder}
        departments={departments}
        folders={folders}
        tags={tags}
      />
      <Card>
        <h2 className='mb-3 text-sm font-semibold'>Documents</h2>
        <div className='mb-3 max-w-xs'>
          <select
            className='w-full rounded-xl border border-slate-200 px-3 py-2 text-sm'
            value={folderFilter}
            onChange={(e) => setFolderFilter(e.target.value)}
          >
            <option value=''>All folders</option>
            {folders.map((folder) => (
              <option key={folder.id} value={folder.id}>
                {folder.name}
              </option>
            ))}
          </select>
        </div>
        <Table>
          <thead>
            <tr className='text-left text-xs uppercase text-slate-500'>
              <th className='pb-2'>Name</th>
              <th className='pb-2'>Folder</th>
              <th className='pb-2'>Status</th>
              <th className='pb-2'>Visibility</th>
              <th className='pb-2'>Created</th>
              <th className='pb-2 text-right'>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredDocuments.map((doc) => (
              <tr key={doc.id} className='border-t border-slate-100'>
                <td className='py-3'>
                  <Link className='text-brand-700 hover:underline' href={`/documents/${doc.id}`}>
                    {doc.original_name}
                  </Link>
                </td>
                <td className='py-3'>{doc.folder_id ? folderNameById.get(doc.folder_id) || 'Unknown' : '-'}</td>
                <td className='py-3'>
                  <Badge>{statusLabel(doc.status)}</Badge>
                </td>
                <td className='py-3'>{doc.visibility}</td>
                <td className='py-3'>{new Date(doc.created_at).toLocaleString()}</td>
                <td className='py-3 text-right'>
                  <div className='flex justify-end gap-2'>
                    <a
                      className='rounded-xl border border-slate-200 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50'
                      href={`${api.baseUrl}/documents/${doc.id}/file`}
                      target='_blank'
                      rel='noopener noreferrer'
                    >
                      View
                    </a>
                    <button
                      className='rounded-xl border border-slate-200 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60'
                      onClick={() => onIndex(doc.id)}
                      type='button'
                      disabled={doc.status === 'processing' || indexingIds.includes(doc.id)}
                    >
                      {doc.status === 'processing' || indexingIds.includes(doc.id) ? 'Indexing...' : 'Index'}
                    </button>
                    <button
                      className='rounded-xl border border-red-200 px-3 py-1 text-xs text-red-700 hover:bg-red-50'
                      onClick={() => onDelete(doc.id, doc.original_name)}
                      type='button'
                    >
                      Delete
                    </button>
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
