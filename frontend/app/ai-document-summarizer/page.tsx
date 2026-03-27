'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import { ChatPanel } from '@/components/ChatPanel';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { useToast } from '@/components/ui/toast';
import { api } from '@/lib/api';
import {
  ChatDoneEvent,
  ChatMessage,
  SummarizerDocument,
  SummarizerMessage,
  SummarizerResponseLanguageMode
} from '@/lib/types';

const LANGUAGE_MODE_STORAGE_KEY = 'kbai.summarizer.languageMode';
const CUSTOM_LANGUAGE_STORAGE_KEY = 'kbai.summarizer.customLanguage';

const LANGUAGE_LABELS: Record<string, string> = {
  de: 'German',
  en: 'English',
  es: 'Spanish',
  fr: 'French',
  it: 'Italian',
  nl: 'Dutch',
  pt: 'Portuguese'
};

function parseSseBlock(block: string): { event: string; data: any } | null {
  const lines = block.split('\n').filter(Boolean);
  if (!lines.length) return null;
  const event = lines.find((line) => line.startsWith('event:'))?.replace('event:', '').trim() || 'message';
  const dataRaw = lines.find((line) => line.startsWith('data:'))?.replace('data:', '').trim() || '{}';
  try {
    return { event, data: JSON.parse(dataRaw) };
  } catch {
    return null;
  }
}

function statusBadgeClass(status: SummarizerDocument['status']): string {
  if (status === 'ready') return 'bg-emerald-100 text-emerald-700';
  if (status === 'processing') return 'bg-amber-100 text-amber-700';
  if (status === 'failed') return 'bg-red-100 text-red-700';
  return 'bg-slate-100 text-slate-700';
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function getBrowserLanguage(): string | undefined {
  if (typeof navigator === 'undefined') return undefined;
  return navigator.language || navigator.languages?.[0] || undefined;
}

function getLanguageLabel(code: string | null | undefined): string {
  if (!code) return 'Not detected yet';
  const normalized = code.toLowerCase();
  const label = LANGUAGE_LABELS[normalized];
  return label ? `${label} (${normalized})` : normalized;
}

export default function AIDocumentSummarizerPage() {
  const [documents, setDocuments] = useState<SummarizerDocument[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [messages, setMessages] = useState<SummarizerMessage[]>([]);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [responseLanguageMode, setResponseLanguageMode] = useState<SummarizerResponseLanguageMode>('auto');
  const [customResponseLanguage, setCustomResponseLanguage] = useState('');
  const [uploading, setUploading] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);
  const { toast, Toast } = useToast();

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId) || null,
    [documents, selectedDocumentId]
  );

  const chatMessages = useMemo<ChatMessage[]>(
    () =>
      messages.map((message) => ({
        ...message,
        session_id: message.document_id
      })),
    [messages]
  );

  const customLanguageRequired = responseLanguageMode === 'custom' && !customResponseLanguage.trim();

  const languagePayload = useMemo(
    () => ({
      response_language_mode: responseLanguageMode,
      custom_response_language:
        responseLanguageMode === 'custom' ? customResponseLanguage.trim() || undefined : undefined,
      browser_language: getBrowserLanguage()
    }),
    [customResponseLanguage, responseLanguageMode]
  );

  const loadDocuments = useCallback(
    async (preferredDocumentId: number | null = null) => {
      const rows = await api.get<SummarizerDocument[]>('/ai-document-summarizer/documents');
      setDocuments(rows);

      const candidateId = preferredDocumentId ?? selectedDocumentId;
      const selected = rows.find((row) => row.id === candidateId) || rows[0] || null;
      setSelectedDocumentId(selected?.id ?? null);
    },
    [selectedDocumentId]
  );

  const loadMessages = useCallback(async (documentId: number | null) => {
    if (!documentId) {
      setMessages([]);
      return;
    }
    const rows = await api.get<SummarizerMessage[]>(
      `/ai-document-summarizer/documents/${documentId}/messages`
    );
    setMessages(rows);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const storedMode = window.localStorage.getItem(LANGUAGE_MODE_STORAGE_KEY);
    const storedCustomLanguage = window.localStorage.getItem(CUSTOM_LANGUAGE_STORAGE_KEY);
    if (storedMode === 'auto' || storedMode === 'document' || storedMode === 'custom') {
      setResponseLanguageMode(storedMode);
    }
    if (storedCustomLanguage) {
      setCustomResponseLanguage(storedCustomLanguage);
    }
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(LANGUAGE_MODE_STORAGE_KEY, responseLanguageMode);
    if (customResponseLanguage.trim()) {
      window.localStorage.setItem(CUSTOM_LANGUAGE_STORAGE_KEY, customResponseLanguage.trim());
    } else {
      window.localStorage.removeItem(CUSTOM_LANGUAGE_STORAGE_KEY);
    }
  }, [customResponseLanguage, responseLanguageMode]);

  useEffect(() => {
    loadDocuments().catch((error) =>
      toast(`Failed to load external documents: ${(error as Error).message}`)
    );
  }, [loadDocuments]);

  useEffect(() => {
    loadMessages(selectedDocumentId).catch((error) =>
      toast(`Failed to load document chat: ${(error as Error).message}`)
    );
  }, [selectedDocumentId, loadMessages]);

  useEffect(() => {
    const hasRunningJob = documents.some(
      (document) => document.status === 'uploaded' || document.status === 'processing'
    );
    if (!hasRunningJob) return;

    const timer = window.setInterval(() => {
      loadDocuments(selectedDocumentId).catch(() => undefined);
    }, 3000);

    return () => window.clearInterval(timer);
  }, [documents, loadDocuments, selectedDocumentId]);

  const uploadDocument = async () => {
    if (!uploadFile) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      const created = await api.post<SummarizerDocument>(
        '/ai-document-summarizer/documents/upload',
        formData,
        true
      );
      setUploadFile(null);
      toast('External document uploaded and queued for indexing');
      await loadDocuments(created.id);
      await loadMessages(created.id);
    } catch (error) {
      toast(`Upload failed: ${(error as Error).message}`);
    } finally {
      setUploading(false);
    }
  };

  const deleteDocument = async (document: SummarizerDocument) => {
    const confirmed = window.confirm(
      `Delete external document "${document.original_name}"? This also removes its summary and chat history.`
    );
    if (!confirmed) return;

    try {
      await api.delete(`/ai-document-summarizer/documents/${document.id}`, true);
      toast('External document deleted');
      const nextSelected = selectedDocumentId === document.id ? null : selectedDocumentId;
      await loadDocuments(nextSelected);
      if (selectedDocumentId === document.id) {
        setMessages([]);
        setWarning(null);
      }
    } catch (error) {
      toast(`Delete failed: ${(error as Error).message}`);
    }
  };

  const summarizeDocument = async () => {
    if (!selectedDocument) return;
    if (selectedDocument.status !== 'ready') {
      toast('Document must be in "ready" status before summarization');
      return;
    }
    if (customLanguageRequired) {
      toast('Enter a custom response language first.');
      return;
    }

    setSummarizing(true);
    try {
      const result = await api.post<{ summary_text: string; summary_updated_at: string }>(
        `/ai-document-summarizer/documents/${selectedDocument.id}/summarize`,
        languagePayload,
        true
      );
      setDocuments((prev) =>
        prev.map((row) =>
          row.id === selectedDocument.id
            ? {
                ...row,
                summary_text: result.summary_text,
                summary_updated_at: result.summary_updated_at
              }
            : row
        )
      );
      toast('Summary generated');
    } catch (error) {
      toast(`Summarization failed: ${(error as Error).message}`);
    } finally {
      setSummarizing(false);
    }
  };

  const askQuestion = async (text: string) => {
    if (!selectedDocument) {
      toast('Select a document first');
      return;
    }
    if (selectedDocument.status !== 'ready') {
      toast('Document must be ready before chat is available');
      return;
    }
    if (customLanguageRequired) {
      toast('Enter a custom response language first.');
      return;
    }

    setChatLoading(true);
    setWarning(null);

    const tempUserId = Date.now();
    const tempAssistantId = Date.now() + 1;
    const documentId = selectedDocument.id;

    setMessages((prev) => [
      ...prev,
      {
        id: tempUserId,
        document_id: documentId,
        role: 'user',
        content: text,
        created_at: new Date().toISOString()
      },
      {
        id: tempAssistantId,
        document_id: documentId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString()
      }
    ]);

    try {
      const response = await fetch(
        `${api.baseUrl}/ai-document-summarizer/documents/${documentId}/ask`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
          body: JSON.stringify({ question: text, ...languagePayload })
        }
      );
      if (!response.ok) {
        const raw = await response.text();
        throw new Error(raw || `Summarizer chat failed: ${response.status}`);
      }
      if (!response.body) throw new Error('No stream body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fullAnswer = '';
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
              prev.map((message) =>
                message.id === tempAssistantId ? { ...message, content: fullAnswer } : message
              )
            );
          }

          if (parsed.event === 'done') {
            const doneEvent = parsed.data as ChatDoneEvent;
            if (doneEvent.warning) {
              setWarning(doneEvent.warning);
            }
          }

          if (parsed.event === 'error') {
            throw new Error(parsed.data.message || 'Summarizer stream failed');
          }
        }
      }

      const refreshed = await api.get<SummarizerMessage[]>(
        `/ai-document-summarizer/documents/${documentId}/messages`
      );
      setMessages(refreshed);
    } catch (error) {
      const text = `Chat failed: ${(error as Error).message}`;
      setWarning(text);
      setMessages((prev) =>
        prev.map((message) =>
          message.id === tempAssistantId ? { ...message, content: text } : message
        )
      );
    } finally {
      setChatLoading(false);
    }
  };

  const onCopy = async (_messageId: number, content: string) => {
    try {
      if (!navigator.clipboard) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(content);
      toast('Copied to clipboard');
    } catch {
      toast('Copy failed. Please copy manually.');
    }
  };

  return (
    <div className='grid h-[calc(100vh-130px)] gap-4 lg:grid-cols-[320px_1fr]'>
      <Card className='overflow-auto'>
        <div className='space-y-3'>
          <div>
            <h2 className='text-sm font-semibold'>AI Document Summarizer</h2>
            <p className='mt-1 text-xs text-slate-500'>
              Upload external documents. These files are isolated and not part of internal company
              knowledge.
            </p>
          </div>

          <input
            type='file'
            accept='.pdf,.txt,.csv,.docx'
            onChange={(event) => setUploadFile(event.target.files?.[0] || null)}
            className='w-full rounded-xl border border-slate-200 px-3 py-2 text-sm'
          />
          <Button onClick={uploadDocument} disabled={!uploadFile || uploading} type='button'>
            {uploading ? 'Uploading...' : 'Upload External Document'}
          </Button>
          <p className='text-[11px] text-slate-400'>
            Supported: PDF, TXT, CSV, DOCX. Legacy DOC is not supported.
          </p>

          <div className='border-t border-slate-100 pt-2'>
            <h3 className='text-xs font-semibold uppercase text-slate-500'>Your External Documents</h3>
            <div className='mt-2 space-y-2'>
              {documents.map((document) => (
                <div
                  key={document.id}
                  className={`rounded-xl border p-2 ${
                    selectedDocumentId === document.id
                      ? 'border-brand-300 bg-brand-50'
                      : 'border-slate-200'
                  }`}
                >
                  <button
                    type='button'
                    className='w-full text-left'
                    onClick={() => {
                      setSelectedDocumentId(document.id);
                      setWarning(null);
                    }}
                  >
                    <p className='truncate text-sm font-medium text-slate-800'>
                      {document.original_name}
                    </p>
                    <div className='mt-1 flex items-center gap-2'>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${statusBadgeClass(
                          document.status
                        )}`}
                      >
                        {document.status}
                      </span>
                      <span className='text-[11px] text-slate-400'>{formatDate(document.created_at)}</span>
                    </div>
                  </button>
                  <div className='mt-2 flex justify-end'>
                    <button
                      type='button'
                      onClick={() => deleteDocument(document)}
                      className='rounded-lg border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50'
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {!documents.length ? (
                <p className='text-sm text-slate-500'>No external documents uploaded yet.</p>
              ) : null}
            </div>
          </div>
        </div>
      </Card>

      <div className='space-y-3'>
        <Card>
          <div className='space-y-3'>
            <div className='flex flex-wrap items-center justify-between gap-2'>
              <div>
                <h2 className='text-sm font-semibold'>Document Summary</h2>
                <p className='mt-1 text-xs text-slate-500'>
                  Generate a concise summary of the most important information.
                </p>
              </div>
              <Button
                onClick={summarizeDocument}
                disabled={
                  !selectedDocument ||
                  selectedDocument.status !== 'ready' ||
                  summarizing ||
                  customLanguageRequired
                }
                type='button'
              >
                {summarizing ? 'Summarizing...' : 'Summarize the most important information'}
              </Button>
            </div>

            <div className='grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 md:grid-cols-[220px_1fr]'>
              <div className='space-y-1'>
                <label className='text-xs font-semibold uppercase tracking-wide text-slate-500'>
                  Response Language
                </label>
                <Select
                  value={responseLanguageMode}
                  onChange={(event) =>
                    setResponseLanguageMode(event.target.value as SummarizerResponseLanguageMode)
                  }
                >
                  <option value='auto'>Auto (browser, then document, then English)</option>
                  <option value='document'>Document language</option>
                  <option value='custom'>Custom language</option>
                </Select>
              </div>
              <div className='space-y-2 text-xs text-slate-500'>
                {responseLanguageMode === 'custom' ? (
                  <div className='space-y-1'>
                    <label className='font-semibold uppercase tracking-wide text-slate-500'>
                      Custom Language
                    </label>
                    <Input
                      value={customResponseLanguage}
                      onChange={(event) => setCustomResponseLanguage(event.target.value)}
                      placeholder='Deutsch, English, Español, Français'
                    />
                  </div>
                ) : null}
                <p>
                  This shared setting applies to both the one-click summary and the document chat.
                  Auto uses your browser language first, then the detected document language, then
                  English.
                </p>
                <p>
                  Detected document language:{' '}
                  <span className='font-medium text-slate-700'>
                    {getLanguageLabel(selectedDocument?.detected_language_code)}
                  </span>
                </p>
                {customLanguageRequired ? (
                  <p className='text-amber-700'>
                    Enter a custom response language before generating a summary or asking
                    document-specific questions.
                  </p>
                ) : null}
              </div>
            </div>
          </div>
        </Card>

        <Card>
          {!selectedDocument ? (
            <p className='text-sm text-slate-500'>Select an external document to view summary and chat.</p>
          ) : (
            <div className='space-y-2'>
              <div className='flex flex-wrap items-center gap-2'>
                <p className='text-sm font-semibold text-slate-800'>{selectedDocument.original_name}</p>
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${statusBadgeClass(
                    selectedDocument.status
                  )}`}
                >
                  {selectedDocument.status}
                </span>
              </div>
              <p className='text-xs text-slate-500'>
                Last summary update: {formatDate(selectedDocument.summary_updated_at)}
              </p>
              {selectedDocument.error_text ? (
                <p className='rounded-xl border border-red-200 bg-red-50 p-2 text-sm text-red-700'>
                  {selectedDocument.error_text}
                </p>
              ) : null}
              {selectedDocument.summary_text ? (
                <article className='whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700'>
                  {selectedDocument.summary_text}
                </article>
              ) : (
                <p className='text-sm text-slate-500'>
                  No summary generated yet. Click the summarize button when document status is ready.
                </p>
              )}
            </div>
          )}
        </Card>

        {warning ? (
          <Card className='border-amber-200 bg-amber-50'>
            <p className='text-sm text-amber-800'>{warning}</p>
          </Card>
        ) : null}

        <div className='h-[calc(100vh-430px)]'>
          <ChatPanel
            messages={chatMessages}
            onSend={askQuestion}
            loading={chatLoading}
            onCopy={onCopy}
            placeholder='Ask a question about the selected external document...'
            sendLabel='Ask about document'
          />
        </div>
      </div>
      <Toast />
    </div>
  );
}
