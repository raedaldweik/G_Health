import { useEffect, useState } from 'react';
import { getDashboard } from '../services/api';
import DynamicChart from '../components/DynamicChart';
import { KpiStrip, Panel, Spinner } from '../components/ui';

const KPI_META = [
  { icon: 'users', tone: 'sand' },
  { icon: 'droplet', tone: 'rose', trend: '0.3pp YoY', trendDir: 'up' },
  { icon: 'check', tone: 'green' },
  { icon: 'alert', tone: 'maroon' },
  { icon: 'droplet', tone: 'red' },
  { icon: 'coins', tone: 'gold' },
];

/** Dashboard 1 — The nation's pulse: who we serve, how we're doing, where demand goes. */
export default function DashboardOverview() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { getDashboard('overview').then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="p-8 text-[13px]" style={{ color: 'var(--red)' }}>Dashboard unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const visits = [
    ...d.visits.history.map((h) => ({ month: h.month, Actual: h.visits })),
    ...d.visits.forecast.map((f) => ({ month: f.month, Forecast: f.visits })),
  ];
  // Top 10 facilities, short labels — 3D bars need breathing room
  const fac = d.facility_benchmark.slice(0, 10).map((f) => {
    const name = f.facility_name.replace(' Health Center', '').replace(' General Hospital', '')
      .replace(' Hospital', '').trim();
    const words = name.split(' ');
    return { facility: words.length > 1 ? words.slice(0, 2).join(' ') : name, controlled: f.pct_controlled };
  });

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5">
      <div className="flex items-end justify-between shrink-0 px-1">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Registry Overview — the national diabetes population
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
            Every figure on this page is the same query the assistant runs in conversation.
          </p>
        </div>
        <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>Synthetic QHIE diabetes cohort · 4,000 patients · 36 months</p>
      </div>

      <KpiStrip items={d.kpis.map((k, i) => ({ ...k, ...KPI_META[i] }))} />

      <div className="flex-1 grid grid-cols-6 grid-rows-2 gap-2.5 min-h-0">
        <div className="col-span-4">
          <Panel title="National mean HbA1c — 36-month trend">
            <DynamicChart bare spec={{
              type: 'line', xKey: 'month',
              data: d.hba1c_trend.map((t) => ({ month: t.month, 'Mean HbA1c': t.mean_hba1c })),
              yKeys: [{ key: 'Mean HbA1c', label: 'Mean HbA1c %' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title={`Ambulatory demand — 12-mo forecast (+${d.visits.yoy_growth_pct}%)`}>
            <DynamicChart bare spec={{
              type: 'line', xKey: 'month', data: visits,
              yKeys: [{ key: 'Actual', label: 'Actual' }, { key: 'Forecast', label: 'Forecast' }],
            }} />
          </Panel>
        </div>

        <div className="col-span-3">
          <Panel title="Facility benchmark — % well-controlled (top 10)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'facility', data: fac,
              yKeys: [{ key: 'controlled', label: '% well-controlled' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Registry risk tiers (rule-based, today)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'band',
              data: d.risk_distribution.map((r) => ({ band: r.band, patients: r.patients })),
              yKeys: [{ key: 'patients', label: 'Patients' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-1">
          <Panel title="Complications & comorbidities">
            <div className="overflow-y-auto h-full px-1">
              {d.complication_prevalence.map((c, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-[rgba(15,23,42,0.05)] last:border-0">
                  <span className="text-[10px] font-semibold leading-tight pr-1" style={{ color: 'var(--text-md)' }}>
                    {c.condition}
                  </span>
                  <span className="text-[10.5px] font-extrabold shrink-0" style={{ color: 'var(--text)' }}>
                    {c.prevalence_pct}%
                  </span>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
