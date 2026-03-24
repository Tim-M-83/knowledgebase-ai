'use client';

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import { LabelValue } from '@/lib/types';

export function TopTagsChart({ data }: { data: LabelValue[] }) {
  return (
    <div className='h-64 w-full'>
      <ResponsiveContainer width='100%' height='100%'>
        <BarChart data={data}>
          <XAxis dataKey='label' />
          <YAxis />
          <Tooltip />
          <Bar dataKey='value' fill='#2f47a4' radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
