import { useEffect, useMemo, useState } from 'react';
import { getDashboard } from '../services/api';
import DynamicChart from '../components/DynamicChart';
import FilterBar from '../components/FilterBar';
import { KpiStrip, Panel, Spinner } from '../components/ui';
import { useApp } from '../context/AppContext';

const KPI_META = [
  { icon: 'users', tone: 'sand' },
  { icon: 'droplet', tone: 'rose' },
  { icon: 'check', tone: 'green' },
  { icon: 'alert', tone: 'maroon' },
  { icon: 'droplet', tone: 'red' },
  { icon: 'coins', tone: 'gold' },
];

const shortFacility = (name) => {
  const n = name.replace(' Health Center', '').replace(' General Hospital', '').replace(' Hospital', '').trim();
  const words = n.split(' ');
  return words.length > 1 ? words.slice(0, 2).join(' ') : n;
};

/** Dashboard 1: the registry at national level. Every panel answers to the cross-filter. */
export default function DashboardOverview() {
  const { dashFilter, toggleFilter } = useApp();
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let alive = true;
    setBusy(true);
    getDashboard('overview', dashFilter).then((r) => { if (alive) { setD(r); setBusy(false); } })
      .catch((e) => { if (alive) { setErr(e.message); setBusy(false); } });
    return () => { alive = false; };
  }, [dashFilter]);

  const fac = useMemo(() => (d ? d.facility_benchmark.slice(0, 10).map((f) => ({
    facility: shortFacility(f.facility_name), full: f.facility_name, controlled: f.pct_controlled,
  })) : []), [d]);
  const facShort = useMemo(() => Object.fromEntries(fac.map((f) => [f.facility, f.full])), [fac]);
  const activeFac = dashFilter.facility ? fac.find((f) => f.full === dashFilter.facility)?.facility ?? null : null;

  if (err) return <div className="p-8 text-[13px]" style={{ color: 'var(--red)' }}>Dashboard unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const visits = [
    ...d.visits.history.map((h) => ({ month: h.month, Actual: h.visits })),
    ...d.visits.forecast.map((f) => ({ month: f.month, Forecast: f.visits })),
  ];
  const filtered = Object.keys(dashFilter).length > 0;

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5" style={{ opacity: busy ? 0.75 : 1, transition: 'opacity 0.2s' }}>
      <div className="flex items-end justify-between gap-4 shrink-0 px-1">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Registry Overview
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
            The national diabetes population. Every figure on this page is the same query the assistant runs in conversation.
          </p>
        </div>
        <FilterBar info={d.filter} />
      </div>

      <KpiStrip items={d.kpis.map((k, i) => ({ ...k, ...KPI_META[i] }))} />

      <div className="flex-1 grid grid-cols-6 grid-rows-2 gap-2.5 min-h-0">
        <div className="col-span-4">
          <Panel title={filtered ? 'Mean HbA1c trend, 36 months (filtered patients)' : 'National mean HbA1c trend, 36 months'}>
            <DynamicChart bare spec={{
              type: 'line', xKey: 'month',
              data: d.hba1c_trend.map((t) => ({ month: t.month, 'Mean HbA1c': t.mean_hba1c })),
              yKeys: [{ key: 'Mean HbA1c', label: 'Mean HbA1c %' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title={`Ambulatory demand, 12-month forecast (+${d.visits.yoy_growth_pct}%, national)`}>
            <DynamicChart bare spec={{
              type: 'line', xKey: 'month', data: visits,
              yKeys: [{ key: 'Actual', label: 'Actual' }, { key: 'Forecast', label: 'Forecast' }],
            }} />
          </Panel>
        </div>

        <div className="col-span-3">
          <Panel title="Facility benchmark: % well-controlled (top 10)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'facility', data: fac,
              yKeys: [{ key: 'controlled', label: '% well-controlled' }],
            }} onSelect={(label) => toggleFilter('facility', facShort[label] || null)} activeLabel={activeFac} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Registry risk tiers (rule-based)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'band',
              data: d.risk_distribution.map((r) => ({ band: r.band, patients: r.patients })),
              yKeys: [{ key: 'patients', label: 'Patients' }],
            }} onSelect={(label) => toggleFilter('tier', label)} activeLabel={dashFilter.tier || null} />
          </Panel>
        </div>
        <div className="col-span-1">
          <Panel title="Complications and comorbidities">
            <div className="overflow-y-auto h-full px-1">
              {d.complication_prevalence.map((c, i) => (
                <div key={i} onClick={() => toggleFilter('condition', c.condition)}
                  className={`row-pick flex items-center justify-between py-1.5 px-1 rounded border-b border-[rgba(15,23,42,0.05)] last:border-0 ${dashFilter.condition === c.condition ? 'picked' : ''}`}>
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
