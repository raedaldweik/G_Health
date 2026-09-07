import { useEffect, useState } from 'react';
import { getDashboard } from '../services/api';
import DynamicChart from '../components/DynamicChart';
import { KpiTile, Panel, Spinner } from '../components/ui';

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
  const fac = d.facility_benchmark.map((f) => ({
    facility: f.facility_name.replace(' Health Center', '').replace(' General Hospital', ' GH').replace(' Hospital', ' H.'),
    controlled: f.pct_controlled,
  }));

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5">
      <div className="flex items-end justify-between shrink-0 px-1">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            National Overview — the nation's pulse
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
            One source of truth: every figure here is the same query the assistant runs in chat.
          </p>
        </div>
        <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>Synthetic QHIE cohort · me-central1 (Doha) target region</p>
      </div>

      <div className="grid grid-cols-6 gap-2.5 shrink-0">
        {d.kpis.map((k, i) => <KpiTile key={i} {...k} />)}
      </div>

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
          <Panel title="Facility benchmark — % of diabetes cohort well-controlled">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'facility', data: fac,
              yKeys: [{ key: 'controlled', label: '% well-controlled' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Cardiovascular risk pyramid">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'band',
              data: d.risk_distribution.map((r) => ({ band: r.band, patients: r.patients })),
              yKeys: [{ key: 'patients', label: 'Patients' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-1">
          <Panel title="CVD prevalence">
            <div className="overflow-y-auto h-full px-1">
              {d.cvd_prevalence.map((c, i) => (
                <div key={i} className="flex items-center justify-between py-1.5 border-b border-[rgba(15,23,42,0.05)] last:border-0">
                  <span className="text-[10px] font-semibold leading-tight pr-1" style={{ color: 'var(--text-md)' }}>
                    {c.condition.replace('Established CVD (any)', 'Established CVD')}
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
