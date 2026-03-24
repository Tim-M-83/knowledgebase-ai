'use client';

import { SourceRef } from '@/lib/types';
import { Card } from '@/components/ui/card';
import Link from 'next/link';

export function SourcesPanel({ sources }: { sources: SourceRef[] }) {
  return (
    <Card className='h-full overflow-auto'>
      <h3 className='mb-3 text-sm font-semibold text-ink'>Sources</h3>
      {sources.length === 0 ? (
        <p className='text-sm text-slate-500'>No sources for the selected assistant answer.</p>
      ) : null}
      <div className='space-y-3'>
        {sources.map((source) => (
          <div key={source.id} className='rounded-xl border border-slate-200 p-3'>
            <p className='text-xs font-semibold text-brand-700'>[{source.id}] {source.original_name}</p>
            <p className='mt-1 text-xs text-slate-500'>
              {source.page_number ? `Page ${source.page_number}` : ''}
              {source.csv_row_start ? `Rows ${source.csv_row_start}-${source.csv_row_end}` : ''}
            </p>
            <p className='mt-2 max-h-24 overflow-hidden text-sm text-slate-700'>{source.snippet}</p>
            <Link href={`/documents/${source.document_id}`} className='mt-2 inline-block text-xs text-brand-700 hover:underline'>
              Open document
            </Link>
          </div>
        ))}
      </div>
    </Card>
  );
}
