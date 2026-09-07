import { useEffect, useMemo, useState } from 'react';
import { getDashboard } from '../services/api';
import MapCard from '../components/MapCard';
import { Bar3D } from '../components/Chart3D';
import { KpiStrip, Panel, Spinner } from '../components/ui';

/** Dashboard 5 — Geography: control is a Doha phenomenon. The equity gradient, on a map. */
export default function DashboardMap() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [metric, setMetric] = useState('pct_controlled');
  const [selected, setSelected] = useState(null);
  const [view, setView] = useState('qatar');

  useEffect(() => { getDashboard('map').then(setD).catch((e) => setErr(e.message)); }, []);

  const spec = useMemo(() => {
    if (!d) return null;
    const meta = d.metric_meta[metric];
    return {
      type: 'map', metric, metric_label: meta.label, worse_is_high: meta.worse_is_high,
      facilities: d.facilities.map((f) => ({ ...f, value: f[metric] })),
      highlight: d.facilities.filter((f) => f.status === 'flagged').map((f) => f.name),
    };
  }, [d, metric]);

  if (err) return <div className="p-8 text-[13px]" style={{ color: 'var(--red)' }}>Dashboard unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const meta = d.metric_meta[metric];
  const ranked = [...d.facilities].sort((a, b) => meta.worse_is_high ? b[metric] - a[metric] : a[metric] - b[metric]);
  const flagged = d.facilities.filter((f) => f.status === 'flagged');
  const regions = d.regions;
  const outsideDoha = regions.filter((r) => r.region !== 'Doha').reduce((s, r) => s + r.statin_gap, 0);
  const sel = d.facilities.find((f) => f.facility_id === selected);
  const fmt = (v) => metric === 'mean_cost' ? `QAR ${Math.round(v).toLocaleString()}`
    : (metric === 'pct_controlled' || metric === 'mean_risk_pct') ? `${v}%` : v;

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5">
      <div className="flex items-end justify-between shrink-0 px-1">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Geography — control is a Doha phenomenon
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
            The further from the capital — and the closer to the Industrial Area — the worse the control. Distance and the equity gradient are the same line.
          </p>
        </div>
        <p className="text-[10px]" style={{ color: 'var(--text-faint)' }}>18 facilities · HMC hospitals + PHCC health centres · gold ring = flagged</p>
      </div>

      <KpiStrip items={[
        { icon: 'alert', tone: 'red', label: 'Flagged facilities (below the line)', value: flagged.length },
        { icon: 'activity', tone: 'maroon', label: `Heaviest gap load — ${regions[0].region}`, value: regions[0].gaps_per_100, suffix: '/100 pts' },
        { icon: 'check', tone: 'green', label: `Best control — ${[...regions].sort((a, b) => b.pct_controlled - a.pct_controlled)[0].region}`,
          value: [...regions].sort((a, b) => b.pct_controlled - a.pct_controlled)[0].pct_controlled, suffix: '%' },
        { icon: 'heart', tone: 'gold', label: 'Statin-gap patients outside Doha', value: outsideDoha },
      ]} />

      <div className="flex-1 grid grid-cols-6 grid-rows-2 gap-2.5 min-h-0">
        <div className="col-span-4 row-span-2">
          <Panel title="Facility map — sized by patients, coloured by metric" pad={false}
            right={
              <div className="flex items-center gap-2">
              <div className="seg-track" style={{ padding: 2 }}>
                {[['qatar', 'Qatar'], ['doha', 'Greater Doha']].map(([k, label]) => (
                  <button key={k} onClick={() => setView(k)} className={`seg-pill ${view === k ? 'active' : ''}`}
                    style={{ fontSize: 10, padding: '4px 9px' }}>{label}</button>
                ))}
              </div>
              <div className="seg-track" style={{ padding: 2 }}>
                {Object.entries(d.metrics).slice(0, 5).map(([k, label]) => (
                  <button key={k} onClick={() => setMetric(k)}
                    className={`seg-pill ${metric === k ? 'active' : ''}`}
                    style={{ fontSize: 10, padding: '4px 9px' }}>
                    {label.split(' (')[0].replace('Open care gaps per 100 patients', 'Gaps / 100').replace('Mean 12-mo event risk', 'Model risk').replace('Mean annual cost per patient', 'Cost / patient').replace('% well-controlled', 'Controlled').replace('Statin-gap patients', 'Statin gap')}
                  </button>
                ))}
              </div>
              </div>
            }>
            <div className="h-full px-2 pb-2">
              <MapCard spec={spec} height="100%" compact onSelect={setSelected} selectedId={selected} view={view} />
            </div>
          </Panel>
        </div>

        <div className="col-span-2">
          <Panel title={`Ranked — ${meta.label} (${meta.worse_is_high ? 'worst first' : 'lowest first'})`} pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-2">
              {ranked.map((f, i) => (
                <button key={f.facility_id} onClick={() => setSelected(f.facility_id === selected ? null : f.facility_id)}
                  className="w-full flex items-center gap-2 py-1.5 border-b border-[rgba(15,23,42,0.05)] last:border-0 text-left transition-all"
                  style={{ background: selected === f.facility_id ? 'rgba(138,21,56,0.07)' : 'transparent' }}>
                  <span className="w-5 text-[9.5px] font-bold text-right shrink-0" style={{ color: 'var(--text-faint)' }}>{i + 1}</span>
                  <span className="flex-1 text-[10.5px] font-semibold truncate" style={{ color: 'var(--text-md)' }}>
                    {f.name.replace(' Health Center', '').replace(' General Hospital', ' GH')}
                    <span className="ml-1 text-[9px] font-medium" style={{ color: 'var(--text-faint)' }}>{f.region}</span>
                  </span>
                  <span className="text-[10.5px] font-extrabold shrink-0" style={{ color: f.status === 'flagged' ? 'var(--red)' : 'var(--text)' }}>
                    {fmt(f[metric])}
                  </span>
                  {f.status === 'flagged' && <span className="badge badge-red" style={{ fontSize: 8, padding: '1px 5px' }}>flag</span>}
                  {f.status === 'top' && <span className="badge badge-green" style={{ fontSize: 8, padding: '1px 5px' }}>top</span>}
                </button>
              ))}
            </div>
          </Panel>
        </div>

        <div className="col-span-2">
          <Panel title={sel ? `${sel.name} — profile` : 'Open care gaps per 100 patients — by region'}>
            {sel ? (
              <div className="h-full px-2 py-1 grid grid-cols-2 gap-x-3 gap-y-2 content-start">
                {[['Patients', sel.patients], ['Region', sel.region], ['Type', sel.type],
                  ['Controlled', `${sel.pct_controlled}%`], ['Mean HbA1c', `${sel.mean_hba1c}%`],
                  ['Gaps / 100', sel.gaps_per_100], ['Statin gap', sel.statin_gap],
                  ['Model risk', `${sel.mean_risk_pct}%`], ['Cost / patient', `QAR ${sel.mean_cost.toLocaleString()}`],
                  ['Expat share', `${sel.expat_share_pct}%`], ['Admissions 12m', sel.admissions_12mo]].map(([k, v]) => (
                  <div key={k}>
                    <p className="text-[8.5px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-faint)' }}>{k}</p>
                    <p className="text-[13px] font-extrabold" style={{ color: 'var(--text)' }}>{v}</p>
                  </div>
                ))}
              </div>
            ) : (
              <Bar3D data={regions.map((r) => ({ label: r.region, value: r.gaps_per_100 }))} maxBars={9} />
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
