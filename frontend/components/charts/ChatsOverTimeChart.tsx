'use client';

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { TimePoint } from '@/lib/types';

export function ChatsOverTimeChart({ data }: { data: TimePoint[] }) {
  return (
    <div className='h-64 w-full'>
      <ResponsiveContainer width='100%' height='100%'>
        <LineChart data={data}>
          <XAxis dataKey='date' />
          <YAxis />
          <Tooltip />
          <Line type='monotone' dataKey='value' stroke='#3f5fdc' strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
