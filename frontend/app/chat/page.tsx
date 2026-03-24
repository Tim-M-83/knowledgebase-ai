'use client';

import { useEffect, useMemo, useState } from 'react';

import { ChatPanel } from '@/components/ChatPanel';
import { SourcesPanel } from '@/components/SourcesPanel';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { api } from '@/lib/api';
import { ChatDoneEvent, ChatMessage, ChatSession, ClearSessionsResponse, SourceRef } from '@/lib/types';

function parseSseBlock(block: string): { event: string; data: any } | null {
  const lines = block.split('\n').filter(Boolean);
  if (!lines.length) return null;
  const event = lines.find((l) => l.startsWith('event:'))?.replace('event:', '').trim() || 'message';
  const dataRaw = lines.find((l) => l.startsWith('data:'))?.replace('data:', '').trim() || '{}';
  try {
    return { event, data: JSON.parse(dataRaw) };
  } catch {
    return null;
  }
}

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<SourceRef[]>([]);
  const [currentSession, setCurrentSession] = useState<number | null>(null);
  const [departments, setDepartments] = useState<Array<{ id: number; name: string }>>([]);
  const [tags, setTags] = useState<Array<{ id: number; name: string }>>([]);
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [chatWarning, setChatWarning] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [selectedAssistantMessageId, setSelectedAssistantMessageId] = useState<number | null>(null);

  const onPrint = (messageId: number) => {
    const element = document.getElementById(`assistant-message-${messageId}`);
    if (!element) {
      setChatWarning('Unable to prepare this answer for printing.');
      return;
    }

    const printWindow = window.open('', '_blank', 'noopener,noreferrer,width=900,height=700');
    if (!printWindow) {
      setChatWarning('Print preview was blocked by your browser. Please allow pop-ups and try again.');
      return;
    }

    const printable = element.innerHTML;
    const style = `
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #fff; color: #0f172a; }
      .kb-print-root { max-width: 860px; margin: 0 auto; padding: 32px; line-height: 1.55; font-size: 14px; }
      .kb-print-root h2 { font-size: 18px; margin: 18px 0 8px; color: #0f172a; }
      .kb-print-root p { margin: 8px 0; }
      .kb-print-root ul, .kb-print-root ol { margin: 8px 0 8px 22px; }
      .kb-print-root li { margin: 4px 0; }
      .kb-print-root code { background: #f1f5f9; padding: 2px 6px; border-radius: 6px; }
      .kb-print-root pre { background: #f8fafc; padding: 12px; border-radius: 10px; border: 1px solid #e2e8f0; overflow: auto; }
    `;

    printWindow.document.open();
    printWindow.document.write(
      `<!doctype html><html><head><title>KnowledgeBase AI Answer</title><meta charset="utf-8"/><style>${style}</style></head><body><article class="kb-print-root">${printable}</article></body></html>`
    );
    printWindow.document.close();
    printWindow.focus();

    const triggerPrint = () => {
      printWindow.print();
      printWindow.close();
    };

    if (printWindow.document.readyState === 'complete') {
      setTimeout(triggerPrint, 50);
    } else {
      printWindow.onload = triggerPrint;
    }
  };

  const selectAssistantMessage = (messageId: number) => {
    setSelectedAssistantMessageId(messageId);
    const selected = messages.find((msg) => msg.id === messageId && msg.role === 'assistant');
    setSources(selected?.sources || []);
  };

  const reloadSessions = async () => {
    const data = await api.get<ChatSession[]>('/chat/sessions');
    setSessions(data);
    if (!currentSession && data.length) {
      setCurrentSession(data[0].id);
    }
  };

  useEffect(() => {
    reloadSessions().catch(() => undefined);
    api.get<Array<{ id: number; name: string }>>('/departments').then(setDepartments).catch(() => undefined);
    api.get<Array<{ id: number; name: string }>>('/tags').then(setTags).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!currentSession) {
      setMessages([]);
      setSources([]);
      setSelectedAssistantMessageId(null);
      return;
    }
    api
      .get<ChatMessage[]>(`/chat/sessions/${currentSession}`)
      .then(setMessages)
      .catch(() => undefined);
  }, [currentSession]);

  useEffect(() => {
    if (loading) return;
    const assistantMessages = messages.filter((msg) => msg.role === 'assistant');
    if (!assistantMessages.length) {
      setSelectedAssistantMessageId(null);
      setSources([]);
      return;
    }

    const currentSelected = assistantMessages.find((msg) => msg.id === selectedAssistantMessageId);
    const chosen =
      currentSelected ||
      [...assistantMessages].reverse().find((msg) => (msg.sources || []).length > 0) ||
      assistantMessages[assistantMessages.length - 1];

    setSelectedAssistantMessageId(chosen.id);
    setSources(chosen.sources || []);
  }, [messages, loading, selectedAssistantMessageId]);

  const sessionTitle = useMemo(
    () => sessions.find((s) => s.id === currentSession)?.title || 'New Chat',
    [sessions, currentSession]
  );

  const onSend = async (text: string) => {
    setLoading(true);
    setChatWarning(null);
    setActionMessage(null);
    const tempUserId = Date.now();
    const tempAssistantId = Date.now() + 1;
    setSelectedAssistantMessageId(tempAssistantId);
    setSources([]);

    setMessages((prev) => [
      ...prev,
      {
        id: tempUserId,
        session_id: currentSession || -1,
        role: 'user',
        content: text,
        created_at: new Date().toISOString()
      },
      {
        id: tempAssistantId,
        session_id: currentSession || -1,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString()
      }
    ]);

    try {
      const response = await fetch(`${api.baseUrl}/chat/ask`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify({
          session_id: currentSession,
          question: text,
          filters: {
            department_id: departmentFilter ? Number(departmentFilter) : null,
            tag_ids: tagFilter ? [Number(tagFilter)] : null
          }
        })
      });

      if (!response.ok) {
        const raw = await response.text();
        throw new Error(raw || `Chat request failed: ${response.status}`);
      }
      if (!response.body) throw new Error('No stream body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullAnswer = '';
      let finalSessionId: number | null = currentSession;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split('\n\n');
        buffer = chunks.pop() || '';

        for (const chunk of chunks) {
          const parsed = parseSseBlock(chunk);
          if (!parsed) continue;

          if (parsed.event === 'token') {
            fullAnswer += parsed.data.text || '';
            setMessages((prev) =>
              prev.map((msg) => (msg.id === tempAssistantId ? { ...msg, content: fullAnswer } : msg))
            );
          }
          if (parsed.event === 'sources') {
            setSources(parsed.data.items || []);
          }
          if (parsed.event === 'done') {
            const done = parsed.data as ChatDoneEvent;
            finalSessionId = done.session_id;
            if (done.warning) {
              setChatWarning(done.warning);
            } else if (done.low_confidence) {
              setChatWarning(
                'Answer generated with low retrieval confidence. Verify against the cited sources.'
              );
            }
          }
        }
      }

      await reloadSessions();
      if (finalSessionId) {
        setCurrentSession(finalSessionId);
        const refreshed = await api.get<ChatMessage[]>(`/chat/sessions/${finalSessionId}`);
        setMessages(refreshed);
      }
    } catch (error) {
      const text = `Chat failed: ${(error as Error).message}`;
      setChatWarning(text);
      setMessages((prev) =>
        prev.map((msg) => (msg.id === tempAssistantId ? { ...msg, content: text } : msg))
      );
    } finally {
      setLoading(false);
    }
  };

  const clearAllSessions = async () => {
    const confirmed = window.confirm('Clear all your chat sessions? This action cannot be undone.');
    if (!confirmed) return;

    try {
      const result = await api.delete<ClearSessionsResponse>('/chat/sessions', true);
      setSessions([]);
      setMessages([]);
      setSources([]);
      setCurrentSession(null);
      setSelectedAssistantMessageId(null);
      setChatWarning(null);
      setActionMessage(`Cleared ${result.deleted_sessions} session(s).`);
    } catch (error) {
      setChatWarning(`Failed to clear sessions: ${(error as Error).message}`);
    }
  };

  const onFeedback = async (messageId: number, rating: 'up' | 'down') => {
    await api.post('/chat/feedback', { message_id: messageId, rating }, true);
  };

  return (
    <div className='grid h-[calc(100vh-130px)] gap-4 lg:grid-cols-[260px_1fr_340px]'>
      <Card className='overflow-auto'>
        <div className='mb-3 flex items-center justify-between'>
          <h3 className='text-sm font-semibold'>Sessions</h3>
          <div className='flex gap-2'>
            <Button onClick={() => setCurrentSession(null)} variant='secondary'>
              New
            </Button>
            <Button onClick={clearAllSessions} variant='secondary'>
              Clear All
            </Button>
          </div>
        </div>
        <div className='space-y-2'>
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => setCurrentSession(session.id)}
              className={`w-full rounded-xl px-3 py-2 text-left text-sm ${
                currentSession === session.id ? 'bg-brand-50 text-brand-700' : 'hover:bg-slate-100'
              }`}
            >
              {session.title}
            </button>
          ))}
        </div>
      </Card>

      <div className='space-y-3'>
        <Card>
          <div className='grid gap-2 md:grid-cols-2'>
            <Select value={departmentFilter} onChange={(e) => setDepartmentFilter(e.target.value)}>
              <option value=''>All Departments</option>
              {departments.map((dep) => (
                <option key={dep.id} value={dep.id}>
                  {dep.name}
                </option>
              ))}
            </Select>
            <Select value={tagFilter} onChange={(e) => setTagFilter(e.target.value)}>
              <option value=''>All Tags</option>
              {tags.map((tag) => (
                <option key={tag.id} value={tag.id}>
                  {tag.name}
                </option>
              ))}
            </Select>
          </div>
          <p className='mt-2 text-xs text-slate-500'>{sessionTitle}</p>
        </Card>
        {chatWarning ? (
          <Card className='border-amber-200 bg-amber-50'>
            <p className='text-sm text-amber-800'>{chatWarning}</p>
          </Card>
        ) : null}
        {actionMessage ? (
          <Card className='border-emerald-200 bg-emerald-50'>
            <p className='text-sm text-emerald-800'>{actionMessage}</p>
          </Card>
        ) : null}
        <ChatPanel
          messages={messages}
          onSend={onSend}
          loading={loading}
          onFeedback={onFeedback}
          onPrint={onPrint}
          selectedAssistantMessageId={selectedAssistantMessageId}
          onSelectAssistantMessage={selectAssistantMessage}
        />
      </div>

      <SourcesPanel sources={sources} />
    </div>
  );
}
