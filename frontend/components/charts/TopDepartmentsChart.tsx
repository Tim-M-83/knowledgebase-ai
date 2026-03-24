'use client';

import { Pie, PieChart, Cell, ResponsiveContainer, Tooltip } from 'recharts';

import { LabelValue } from '@/lib/types';

const COLORS = ['#3f5fdc', '#2f47a4', '#7391ff', '#9db3ff', '#c3d0ff'];

export function TopDepartmentsChart({ data }: { data: LabelValue[] }) {
  return (
    <div className='h-64 w-full'>
      <ResponsiveContainer width='100%' height='100%'>
        <PieChart>
          <Pie data={data} dataKey='value' nameKey='label' outerRadius={90} label>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
