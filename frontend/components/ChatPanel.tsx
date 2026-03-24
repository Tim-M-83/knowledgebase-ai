'use client';

import { FormEvent, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { ChatMessage } from '@/lib/types';

export function ChatPanel({
  messages,
  onSend,
  loading,
  onFeedback,
  onPrint,
  onCopy,
  selectedAssistantMessageId,
  onSelectAssistantMessage,
  placeholder = 'Ask a question about your company docs...',
  sendLabel = 'Send'
}: {
  messages: ChatMessage[];
  onSend: (text: string) => Promise<void>;
  loading: boolean;
  onFeedback?: (messageId: number, rating: 'up' | 'down') => Promise<void>;
  onPrint?: (messageId: number) => void;
  onCopy?: (messageId: number, content: string) => void;
  selectedAssistantMessageId?: number | null;
  onSelectAssistantMessage?: (messageId: number) => void;
  placeholder?: string;
  sendLabel?: string;
}) {
  const [text, setText] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    const value = text;
    setText('');
    await onSend(value);
  };

  return (
    <Card className='flex h-full flex-col'>
      <div className='mb-4 flex-1 space-y-3 overflow-auto'>
        {messages.map((message) => (
          <div key={message.id} className='space-y-1'>
            <div
              onClick={() => {
                if (message.role === 'assistant' && onSelectAssistantMessage) {
                  onSelectAssistantMessage(message.id);
                }
              }}
              className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                message.role === 'user'
                  ? 'ml-auto bg-brand-500 text-white'
                  : selectedAssistantMessageId === message.id
                    ? 'cursor-pointer border border-brand-300 bg-brand-50 text-slate-800'
                    : 'cursor-pointer border border-slate-200 bg-slate-50 text-slate-800'
              }`}
            >
              {message.role === 'assistant' ? (
                <div id={`assistant-message-${message.id}`} className='kb-markdown break-words'>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                </div>
              ) : (
                <div className='whitespace-pre-wrap break-words'>{message.content}</div>
              )}
            </div>
            {message.role === 'assistant' && (onFeedback || onPrint || onCopy) ? (
              <div className='flex max-w-[85%] gap-2'>
                {onCopy ? (
                  <button
                    className='rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-100'
                    onClick={() => onCopy(message.id, message.content)}
                    type='button'
                  >
                    Copy
                  </button>
                ) : null}
                {onFeedback ? (
                  <>
                    <button
                      className='rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-100'
                      onClick={() => onFeedback(message.id, 'up')}
                      type='button'
                    >
                      Upvote
                    </button>
                    <button
                      className='rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-100'
                      onClick={() => onFeedback(message.id, 'down')}
                      type='button'
                    >
                      Downvote
                    </button>
                  </>
                ) : null}
                {onPrint ? (
                  <button
                    className='rounded-lg border border-slate-200 px-2 py-1 text-xs hover:bg-slate-100'
                    onClick={() => onPrint(message.id)}
                    type='button'
                  >
                    Print
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        ))}
      </div>
      <form onSubmit={submit} className='space-y-2'>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder={placeholder}
        />
        <div className='flex justify-end'>
          <Button disabled={loading}>{loading ? 'Thinking...' : sendLabel}</Button>
        </div>
      </form>
    </Card>
  );
}
