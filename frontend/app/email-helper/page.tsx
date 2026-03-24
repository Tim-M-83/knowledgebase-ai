'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';

import { ChatPanel } from '@/components/ChatPanel';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useToast } from '@/components/ui/toast';
import { api } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import { ChatDoneEvent, ChatMessage, ChatSession } from '@/lib/types';

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

export default function EmailHelperPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentSession, setCurrentSession] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkingAccess, setCheckingAccess] = useState(true);
  const [disabledNotice, setDisabledNotice] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const { toast, Toast } = useToast();
  const redirectTimerRef = useRef<number | null>(null);

  const loadSessions = async () => {
    const data = await api.get<ChatSession[]>('/email-helper/sessions');
    setSessions(data);
    if (!currentSession && data.length) {
      setCurrentSession(data[0].id);
    }
  };

  useEffect(() => {
    let active = true;

    const bootstrap = async () => {
      try {
        const user = await getCurrentUser();
        if (!active) return;

        if (!user) {
          router.replace('/login');
          return;
        }

        if (!user.email_helper_enabled) {
          setDisabledNotice('Email Helper is currently disabled by your admin. Redirecting to Dashboard...');
          redirectTimerRef.current = window.setTimeout(() => {
            router.replace('/dashboard');
          }, 1200);
          return;
        }

        await loadSessions();
      } catch {
        router.replace('/dashboard');
      } finally {
        if (active) {
          setCheckingAccess(false);
        }
      }
    };

    bootstrap().catch(() => undefined);

    return () => {
      active = false;
      if (redirectTimerRef.current) {
        window.clearTimeout(redirectTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!currentSession || checkingAccess || disabledNotice) {
      if (!currentSession) {
        setMessages([]);
      }
      return;
    }

    api
      .get<ChatMessage[]>(`/email-helper/sessions/${currentSession}`)
      .then(setMessages)
      .catch((error) => {
        toast(`Failed to load archived email chat: ${(error as Error).message}`);
      });
  }, [currentSession, checkingAccess, disabledNotice]);

  const startNewChat = () => {
    setCurrentSession(null);
    setMessages([]);
    setWarning(null);
  };

  const deleteSession = async (sessionId: number) => {
    const target = sessions.find((s) => s.id === sessionId);
    const confirmed = window.confirm(
      `Delete archived email chat "${target?.title || sessionId}"? This cannot be undone.`
    );
    if (!confirmed) return;

    try {
      await api.delete(`/email-helper/sessions/${sessionId}`, true);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (currentSession === sessionId) {
        setCurrentSession(null);
        setMessages([]);
      }
      toast('Archived email chat deleted');
    } catch (error) {
      toast(`Delete failed: ${(error as Error).message}`);
    }
  };

  const onSend = async (text: string) => {
    setLoading(true);
    setWarning(null);

    const tempUserId = Date.now();
    const tempAssistantId = Date.now() + 1;

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
      const response = await fetch(`${api.baseUrl}/email-helper/ask`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify({
          session_id: currentSession,
          email_text: text
        })
      });

      if (!response.ok) {
        const raw = await response.text();
        throw new Error(raw || `Email helper request failed: ${response.status}`);
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

          if (parsed.event === 'done') {
            const doneEvent = parsed.data as ChatDoneEvent;
            finalSessionId = doneEvent.session_id;
            if (doneEvent.warning) {
              setWarning(doneEvent.warning);
            }
          }

          if (parsed.event === 'error') {
            throw new Error(parsed.data.message || 'Email helper stream failed');
          }
        }
      }

      await loadSessions();
      if (finalSessionId) {
        setCurrentSession(finalSessionId);
        const refreshed = await api.get<ChatMessage[]>(`/email-helper/sessions/${finalSessionId}`);
        setMessages(refreshed);
      }
    } catch (error) {
      const text = `Email helper failed: ${(error as Error).message}`;
      setWarning(text);
      setMessages((prev) => prev.map((msg) => (msg.id === tempAssistantId ? { ...msg, content: text } : msg)));
    } finally {
      setLoading(false);
    }
  };

  const onCopy = async (_messageId: number, content: string) => {
    try {
      if (!navigator.clipboard) {
        throw new Error('Clipboard API not available');
      }
      await navigator.clipboard.writeText(content);
      toast('Email reply copied to clipboard');
    } catch {
      toast('Copy failed. Please copy manually.');
    }
  };

  if (checkingAccess) {
    return (
      <Card>
        <p className='text-sm text-slate-600'>Checking Email Helper access...</p>
      </Card>
    );
  }

  if (disabledNotice) {
    return (
      <Card className='border-amber-200 bg-amber-50'>
        <p className='text-sm text-amber-800'>{disabledNotice}</p>
      </Card>
    );
  }

  return (
    <div className='grid h-[calc(100vh-130px)] gap-4 lg:grid-cols-[280px_1fr]'>
      <Card className='overflow-auto'>
        <div className='mb-3 flex items-center justify-between'>
          <h3 className='text-sm font-semibold'>Email Archive</h3>
          <Button onClick={startNewChat} variant='secondary'>
            New
          </Button>
        </div>

        <div className='space-y-2'>
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`flex items-center gap-2 rounded-xl border px-2 py-2 ${
                currentSession === session.id ? 'border-brand-300 bg-brand-50' : 'border-slate-200'
              }`}
            >
              <button
                className='flex-1 text-left text-sm text-slate-700'
                onClick={() => setCurrentSession(session.id)}
                type='button'
              >
                {session.title}
              </button>
              <button
                className='rounded-lg border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50'
                onClick={() => deleteSession(session.id)}
                type='button'
              >
                Delete
              </button>
            </div>
          ))}
          {!sessions.length ? <p className='text-sm text-slate-500'>No archived email chats yet.</p> : null}
        </div>
      </Card>

      <div className='space-y-3'>
        <Card>
          <h2 className='text-sm font-semibold'>Email Helper</h2>
          <p className='mt-1 text-xs text-slate-500'>
            Paste the incoming email text and generate a ready-to-send reply grounded in your indexed knowledge.
          </p>
        </Card>

        {warning ? (
          <Card className='border-amber-200 bg-amber-50'>
            <p className='text-sm text-amber-800'>{warning}</p>
          </Card>
        ) : null}

        <ChatPanel
          messages={messages}
          onSend={onSend}
          loading={loading}
          onCopy={onCopy}
          placeholder='Paste an incoming email and press Generate Reply...'
          sendLabel='Generate Reply'
        />
      </div>
      <Toast />
    </div>
  );
}
