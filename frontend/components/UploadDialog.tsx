'use client';

import { FormEvent, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';

export function UploadDialog({
  onUpload,
  onCreateTag,
  onCreateDepartment,
  onCreateFolder,
  departments,
  folders,
  tags,
  allowInlineCreate = true
}: {
  onUpload: (formData: FormData) => Promise<void>;
  onCreateTag: (name: string) => Promise<{ id: number; name: string }>;
  onCreateDepartment: (name: string) => Promise<{ id: number; name: string }>;
  onCreateFolder: (name: string) => Promise<{ id: number; name: string }>;
  departments: Array<{ id: number; name: string }>;
  folders: Array<{ id: number; name: string }>;
  tags: Array<{ id: number; name: string }>;
  allowInlineCreate?: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [departmentId, setDepartmentId] = useState('');
  const [folderId, setFolderId] = useState('');
  const [visibility, setVisibility] = useState('company');
  const [selectedTags, setSelectedTags] = useState<number[]>([]);
  const [newTagName, setNewTagName] = useState('');
  const [newDepartmentName, setNewDepartmentName] = useState('');
  const [newFolderName, setNewFolderName] = useState('');
  const [addingTag, setAddingTag] = useState(false);
  const [addingDepartment, setAddingDepartment] = useState(false);
  const [addingFolder, setAddingFolder] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);

  const toggleTag = (tagId: number) => {
    setSelectedTags((prev) => (prev.includes(tagId) ? prev.filter((id) => id !== tagId) : [...prev, tagId]));
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setErrorText(null);
    const fd = new FormData();
    fd.append('file', file);
    if (departmentId) fd.append('department_id', departmentId);
    if (folderId) fd.append('folder_id', folderId);
    fd.append('visibility', visibility);
    fd.append('tag_ids', selectedTags.join(','));
    await onUpload(fd);
    setFile(null);
    setDepartmentId('');
    setFolderId('');
    setVisibility('company');
    setSelectedTags([]);
  };

  const createTag = async () => {
    const name = newTagName.trim();
    if (!name) return;
    setAddingTag(true);
    setErrorText(null);
    try {
      const created = await onCreateTag(name);
      setSelectedTags((prev) => (prev.includes(created.id) ? prev : [...prev, created.id]));
      setNewTagName('');
    } catch (error) {
      setErrorText(`Tag creation failed: ${(error as Error).message}`);
    } finally {
      setAddingTag(false);
    }
  };

  const createDepartment = async () => {
    const name = newDepartmentName.trim();
    if (!name) return;
    setAddingDepartment(true);
    setErrorText(null);
    try {
      const created = await onCreateDepartment(name);
      setDepartmentId(String(created.id));
      setNewDepartmentName('');
    } catch (error) {
      setErrorText(`Department creation failed: ${(error as Error).message}`);
    } finally {
      setAddingDepartment(false);
    }
  };

  const createFolder = async () => {
    const name = newFolderName.trim();
    if (!name) return;
    setAddingFolder(true);
    setErrorText(null);
    try {
      const created = await onCreateFolder(name);
      setFolderId(String(created.id));
      setNewFolderName('');
    } catch (error) {
      setErrorText(`Folder creation failed: ${(error as Error).message}`);
    } finally {
      setAddingFolder(false);
    }
  };

  return (
    <Card>
      <h3 className='mb-3 text-sm font-semibold text-ink'>Upload Document</h3>
      <form onSubmit={submit} className='grid gap-3 md:grid-cols-2'>
        <Input type='file' accept='.pdf,.txt,.csv' onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <Select value={visibility} onChange={(e) => setVisibility(e.target.value)}>
          <option value='company'>Company</option>
          <option value='department'>Department</option>
          <option value='private'>Private</option>
        </Select>
        <Select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
          <option value=''>No Department</option>
          {departments.map((dep) => (
            <option key={dep.id} value={dep.id}>
              {dep.name}
            </option>
          ))}
        </Select>
        <Select value={folderId} onChange={(e) => setFolderId(e.target.value)}>
          <option value=''>No Folder</option>
          {folders.map((folder) => (
            <option key={folder.id} value={folder.id}>
              {folder.name}
            </option>
          ))}
        </Select>
        {allowInlineCreate ? (
          <div className='flex gap-2'>
            <Input
              placeholder='New department'
              value={newDepartmentName}
              onChange={(e) => setNewDepartmentName(e.target.value)}
            />
            <Button
              type='button'
              variant='secondary'
              onClick={createDepartment}
              disabled={!newDepartmentName.trim() || addingDepartment}
            >
              {addingDepartment ? 'Adding...' : 'Add'}
            </Button>
          </div>
        ) : null}
        {allowInlineCreate ? (
          <div className='flex gap-2'>
            <Input
              placeholder='New folder'
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
            />
            <Button
              type='button'
              variant='secondary'
              onClick={createFolder}
              disabled={!newFolderName.trim() || addingFolder}
            >
              {addingFolder ? 'Adding...' : 'Add'}
            </Button>
          </div>
        ) : null}
        <div className='md:col-span-2'>
          <p className='mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500'>Tags</p>
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
        </div>
        {allowInlineCreate ? (
          <div className='md:col-span-2'>
            <div className='flex gap-2'>
              <Input placeholder='New tag' value={newTagName} onChange={(e) => setNewTagName(e.target.value)} />
              <Button
                type='button'
                variant='secondary'
                onClick={createTag}
                disabled={!newTagName.trim() || addingTag}
              >
                {addingTag ? 'Adding...' : 'Add'}
              </Button>
            </div>
          </div>
        ) : null}
        {errorText ? <p className='md:col-span-2 text-sm text-red-700'>{errorText}</p> : null}
        <div className='md:col-span-2'>
          <Button type='submit'>Upload + Ingest</Button>
        </div>
      </form>
    </Card>
  );
}
