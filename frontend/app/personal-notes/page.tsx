'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/components/ui/toast';
import { api } from '@/lib/api';
import { PersonalNote, PersonalNotePriority } from '@/lib/types';

const DRAFT_TITLE = 'Untitled Note';
const DRAFT_CONTENT = 'Start writing your note...';
const DRAFT_PRIORITY: PersonalNotePriority = 'none';

const PRIORITY_STYLES: Record<
  PersonalNotePriority,
  { label: string; badgeClass: string; cardClass: string }
> = {
  none: {
    label: 'None',
    badgeClass: 'bg-slate-100 text-slate-700',
    cardClass: 'border-slate-200',
  },
  low: {
    label: 'Low',
    badgeClass: 'bg-emerald-100 text-emerald-700',
    cardClass: 'border-emerald-300',
  },
  medium: {
    label: 'Medium',
    badgeClass: 'bg-amber-100 text-amber-700',
    cardClass: 'border-amber-300',
  },
  high: {
    label: 'High',
    badgeClass: 'bg-red-100 text-red-700',
    cardClass: 'border-red-300',
  },
};

function normalizePriority(value?: string): PersonalNotePriority {
  if (value === 'low' || value === 'medium' || value === 'high') {
    return value;
  }
  return 'none';
}

function previewText(content: string): string {
  const compact = content.replace(/\s+/g, ' ').trim();
  if (compact.length <= 90) return compact;
  return `${compact.slice(0, 90)}...`;
}

function formatUpdatedAt(value: string): string {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function PersonalNotesPage() {
  const [notes, setNotes] = useState<PersonalNote[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [priority, setPriority] = useState<PersonalNotePriority>('none');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [creating, setCreating] = useState(false);
  const { toast, Toast } = useToast();

  const loadNotes = useCallback(
    async (preferredId: number | null = null) => {
      const data = await api.get<PersonalNote[]>('/personal-notes');
      setNotes(data);

      const candidateId = preferredId ?? selectedId;
      const selected = data.find((note) => note.id === candidateId) || data[0] || null;

      setSelectedId(selected?.id ?? null);
      setTitle(selected?.title ?? '');
      setContent(selected?.content ?? '');
      setPriority(normalizePriority(selected?.priority));
    },
    [selectedId]
  );

  useEffect(() => {
    let active = true;

    const bootstrap = async () => {
      try {
        await loadNotes();
      } catch (error) {
        if (active) {
          toast(`Failed to load notes: ${(error as Error).message}`);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    bootstrap().catch(() => undefined);
    return () => {
      active = false;
    };
  }, [loadNotes]);

  const filteredNotes = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return notes;
    return notes.filter(
      (note) =>
        note.title.toLowerCase().includes(query) ||
        note.content.toLowerCase().includes(query)
    );
  }, [notes, search]);

  const onSelect = (note: PersonalNote) => {
    setSelectedId(note.id);
    setTitle(note.title);
    setContent(note.content);
    setPriority(normalizePriority(note.priority));
  };

  const onNew = async () => {
    setCreating(true);
    try {
      const created = await api.post<PersonalNote>(
        '/personal-notes',
        {
          title: DRAFT_TITLE,
          content: DRAFT_CONTENT,
          priority: DRAFT_PRIORITY,
        },
        true
      );
      toast('New note created');
      await loadNotes(created.id);
    } catch (error) {
      toast(`Create failed: ${(error as Error).message}`);
    } finally {
      setCreating(false);
    }
  };

  const onSave = async () => {
    const cleanTitle = title.trim();
    const cleanContent = content.trim();
    if (!cleanTitle || !cleanContent) return;

    setSaving(true);
    try {
      if (selectedId) {
        const updated = await api.put<PersonalNote>(
          `/personal-notes/${selectedId}`,
          { title: cleanTitle, content: cleanContent, priority },
          true
        );
        toast('Note updated');
        await loadNotes(updated.id);
      } else {
        const created = await api.post<PersonalNote>(
          '/personal-notes',
          { title: cleanTitle, content: cleanContent, priority },
          true
        );
        toast('Note created');
        await loadNotes(created.id);
      }
    } catch (error) {
      toast(`Save failed: ${(error as Error).message}`);
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async () => {
    if (!selectedId) return;
    const target = notes.find((note) => note.id === selectedId);
    const confirmed = window.confirm(
      `Delete note "${target?.title || selectedId}"? This cannot be undone.`
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await api.delete(`/personal-notes/${selectedId}`, true);
      toast('Note deleted');
      await loadNotes(null);
    } catch (error) {
      toast(`Delete failed: ${(error as Error).message}`);
    } finally {
      setDeleting(false);
    }
  };

  const saveDisabled = saving || !title.trim() || !content.trim();

  return (
    <div className='grid h-[calc(100vh-130px)] gap-4 lg:grid-cols-[320px_1fr]'>
      <Card className='overflow-auto'>
        <div className='mb-3 flex items-center justify-between'>
          <h2 className='text-sm font-semibold'>Personal Notes</h2>
          <Button onClick={onNew} variant='secondary' type='button' disabled={creating}>
            {creating ? 'Creating...' : 'New Note'}
          </Button>
        </div>

        <Input
          placeholder='Search notes...'
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <div className='mt-3 space-y-2'>
          {loading ? <p className='text-sm text-slate-500'>Loading notes...</p> : null}
          {!loading && !filteredNotes.length ? (
            <p className='text-sm text-slate-500'>No notes found.</p>
          ) : null}
          {filteredNotes.map((note) => {
            const notePriority = normalizePriority(note.priority);
            const style = PRIORITY_STYLES[notePriority];
            return (
              <button
                key={note.id}
                type='button'
                onClick={() => onSelect(note)}
                className={`w-full rounded-xl border border-l-4 px-3 py-2 text-left ${
                  selectedId === note.id
                    ? `bg-brand-50 ${style.cardClass}`
                    : `${style.cardClass} hover:bg-slate-50`
                }`}
              >
                <div className='flex items-center justify-between gap-2'>
                  <p className='text-sm font-semibold text-slate-800'>{note.title}</p>
                  <Badge className={style.badgeClass}>{style.label}</Badge>
                </div>
                <p className='mt-1 text-xs text-slate-600'>{previewText(note.content)}</p>
                <p className='mt-1 text-[11px] text-slate-400'>
                  Updated {formatUpdatedAt(note.updated_at)}
                </p>
              </button>
            );
          })}
        </div>
      </Card>

      <div className='space-y-3'>
        <Card>
          <h2 className='text-sm font-semibold'>
            {selectedId ? 'Edit Personal Note' : 'New Personal Note'}
          </h2>
          <p className='mt-1 text-xs text-slate-500'>
            Notes are private to your account and not used for AI responses.
          </p>
        </Card>

        <Card className='flex h-[calc(100vh-230px)] flex-col gap-3'>
          <div className='grid gap-3 sm:grid-cols-[1fr_180px]'>
            <Input
              placeholder='Title'
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              maxLength={160}
            />
            <Select
              value={priority}
              onChange={(event) => setPriority(event.target.value as PersonalNotePriority)}
            >
              <option value='none'>Priority: None</option>
              <option value='low'>Priority: Low</option>
              <option value='medium'>Priority: Medium</option>
              <option value='high'>Priority: High</option>
            </Select>
          </div>
          <Textarea
            placeholder='Write your personal note...'
            value={content}
            onChange={(event) => setContent(event.target.value)}
            className='min-h-[280px] flex-1 resize-y'
          />
          <div className='flex justify-end gap-2'>
            {selectedId ? (
              <Button variant='danger' onClick={onDelete} disabled={deleting} type='button'>
                {deleting ? 'Deleting...' : 'Delete'}
              </Button>
            ) : null}
            <Button onClick={onSave} disabled={saveDisabled} type='button'>
              {saving ? 'Saving...' : 'Save'}
            </Button>
          </div>
        </Card>
      </div>
      <Toast />
    </div>
  );
}
