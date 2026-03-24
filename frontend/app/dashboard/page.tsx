'use client';

import { useEffect, useState } from 'react';

import { KPI } from '@/components/KPI';
import { ChatsOverTimeChart } from '@/components/charts/ChatsOverTimeChart';
import { TopDepartmentsChart } from '@/components/charts/TopDepartmentsChart';
import { TopTagsChart } from '@/components/charts/TopTagsChart';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import { getCurrentUser } from '@/lib/auth';
import { ChartsResponse, ClearGapsResponse, GapItem, KPIResponse, Role } from '@/lib/types';

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPIResponse | null>(null);
  const [charts, setCharts] = useState<ChartsResponse | null>(null);
  const [gaps, setGaps] = useState<GapItem[]>([]);
  const [role, setRole] = useState<Role | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadDashboard = async () => {
    const [kpiData, chartData, gapData] = await Promise.all([
      api.get<KPIResponse>('/dashboard/kpis'),
      api.get<ChartsResponse>('/dashboard/charts'),
      api.get<GapItem[]>('/dashboard/gaps')
    ]);
    setKpis(kpiData);
    setCharts(chartData);
    setGaps(gapData);
  };

  useEffect(() => {
    loadDashboard().catch(() => undefined);
    getCurrentUser().then((user) => setRole(user?.role || null)).catch(() => undefined);
  }, []);

  const clearGaps = async () => {
    const confirmed = window.confirm('Clear the Knowledge Gaps log? This action cannot be undone.');
    if (!confirmed) return;
    try {
      const result = await api.delete<ClearGapsResponse>('/dashboard/gaps', true);
      await loadDashboard();
      setMessage(`Cleared ${result.deleted_gaps} gap entries.`);
    } catch (error) {
      setMessage(`Failed to clear gaps: ${(error as Error).message}`);
    }
  };

  if (!kpis || !charts) {
    return <Skeleton className='h-96' />;
  }

  return (
    <div className='space-y-6'>
      <div className='grid gap-4 md:grid-cols-3 xl:grid-cols-6'>
        <KPI label='Documents' value={kpis.docs} />
        <KPI label='Chunks' value={kpis.chunks} />
        <KPI label='Users' value={kpis.users} />
        <KPI label='Chats' value={kpis.chats} />
        <KPI label='Failed Ingestions' value={kpis.failed_ingestions} />
        <KPI label='Last Ingestion' value={kpis.last_ingestion ? new Date(kpis.last_ingestion).toLocaleDateString() : '-'} />
      </div>

      <div className='grid gap-4 xl:grid-cols-3'>
        <Card className='xl:col-span-2'>
          <h2 className='mb-3 text-sm font-semibold'>Daily Chats</h2>
          <ChatsOverTimeChart data={charts.daily_chats} />
        </Card>
        <Card>
          <h2 className='mb-3 text-sm font-semibold'>Top Departments</h2>
          <TopDepartmentsChart data={charts.top_departments} />
        </Card>
      </div>

      <div className='grid gap-4 xl:grid-cols-2'>
        <Card>
          <h2 className='mb-3 text-sm font-semibold'>Top Tags</h2>
          <TopTagsChart data={charts.top_tags} />
        </Card>
        <Card>
          <div className='mb-3 flex items-center justify-between'>
            <h2 className='text-sm font-semibold'>Knowledge Gaps</h2>
            {role === 'admin' ? (
              <Button variant='secondary' onClick={clearGaps}>
                Clear Knowledge Gaps
              </Button>
            ) : null}
          </div>
          <div className='space-y-2'>
            {gaps.slice(0, 8).map((gap) => (
              <div key={gap.id} className='rounded-xl border border-slate-200 p-2'>
                <p className='text-sm text-ink'>{gap.question}</p>
                <p className='text-xs text-slate-500'>Score: {gap.avg_score.toFixed(2)}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
      {message ? <p className='text-sm text-slate-600'>{message}</p> : null}
    </div>
  );
}
