import { useEffect, useState } from 'react';
import { getDashboard } from '../services/api';
import DynamicChart from '../components/DynamicChart';
import FilterBar from '../components/FilterBar';
import { KpiStrip, Panel, Spinner } from '../components/ui';
import { useApp } from '../context/AppContext';

const shortFacility = (f) => f.replace(' Health Center', '').replace(' Hospital', ' H.');

/** Dashboard 4: cost concentration and descriptive variation by population group. */
export default function DashboardCost() {
  const { dashFilter, toggleFilter } = useApp();
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let alive = true;
    setBusy(true);
    getDashboard('cost', dashFilter).then((r) => { if (alive) { setD(r); setBusy(false); } })
      .catch((e) => { if (alive) { setErr(e.message); setBusy(false); } });
    return () => { alive = false; };
  }, [dashFilter]);
  if (err) return <div className="p-8 text-[13px]" style={{ color: 'var(--red)' }}>Dashboard unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const cc = d.concentration;
  const eq = d.equity;
  const hi = eq[0], lo = eq[eq.length - 1];
  const gapPts = eq.length > 1 ? (hi.mean_hba1c - lo.mean_hba1c).toFixed(2) : '0.00';
  const segments = [...d.segments].sort((a, b) => b.total_cost - a.total_cost);
  const facByShort = Object.fromEntries(d.by_facility.map((f) => [shortFacility(f.facility), f.facility]));
  const activeFac = dashFilter.facility ? shortFacility(dashFilter.facility) : null;

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5" style={{ opacity: busy ? 0.75 : 1, transition: 'opacity 0.2s' }}>
      <div className="flex items-end justify-between gap-4 shrink-0 px-1">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Cost &amp; Population Variation
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
            Where the spend concentrates, and how outcomes vary by population group. Descriptive variation that identifies where further investigation is needed; group differences in this synthetic demonstration data are not causal or biological findings.
          </p>
        </div>
        <FilterBar info={d.filter} />
      </div>

      <KpiStrip items={[
        { icon: 'coins', tone: 'gold', label: 'Total annual cost',
          value: (cc.total_annual_cost_qar / 1e6).toFixed(1), suffix: 'M QAR' },
        { icon: 'users', tone: 'sand', label: 'Share of spend from the costliest 10% of patients',
          value: `${cc.top10pct_share_pct}%` },
        { icon: 'alert', tone: 'red',
          label: eq.length > 1 ? `Spread in mean HbA1c across nationality groups: ${hi.nationality} ${hi.mean_hba1c.toFixed(1)}% vs ${lo.nationality} ${lo.mean_hba1c.toFixed(1)}%` : 'Spread in mean HbA1c across nationality groups',
          value: gapPts, suffix: 'pts' },
        { icon: 'activity', tone: 'violet', label: 'Costliest population segment',
          value: segments[0]?.segment ?? 'n/a' },
      ]} />

      <div className="flex-1 grid grid-cols-6 grid-rows-2 gap-2.5 min-h-0">
        <div className="col-span-2">
          <Panel title="Cost concentration: cumulative share of spend">
            <DynamicChart bare spec={{
              type: 'area', xKey: 'patients',
              data: cc.deciles.map((x) => ({ patients: `${x.top_pct_patients}%`, share: x.pct_of_spend })),
              yKeys: [{ key: 'share', label: 'Cumulative % of spend' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Annual spend by population segment (QAR M)">
            <DynamicChart bare spec={{
              type: 'pie', xKey: 'segment',
              data: segments.map((s) => ({ segment: s.segment, spend: +(s.total_cost / 1e6).toFixed(2) })),
              yKeys: [{ key: 'spend', label: 'QAR (M)' }], centerLabel: 'QAR M',
            }} onSelect={(label) => toggleFilter('segment', label)} activeLabel={dashFilter.segment || ''} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Total spend by facility (QAR M)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'facility',
              data: d.by_facility.slice(0, 10).map((f) => ({ facility: shortFacility(f.facility), spend: f.total_qar_m })),
              yKeys: [{ key: 'spend', label: 'QAR (M)' }],
            }} onSelect={(label) => toggleFilter('facility', facByShort[label] || null)} activeLabel={activeFac} />
          </Panel>
        </div>

        <div className="col-span-3">
          <Panel title="Mean HbA1c by nationality group (descriptive variation)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'nationality',
              data: eq.map((e) => ({ nationality: e.nationality, HbA1c: e.mean_hba1c })),
              yKeys: [{ key: 'HbA1c', label: 'Mean HbA1c %' }],
            }} onSelect={(label) => toggleFilter('nationality', label)} activeLabel={dashFilter.nationality || null} />
          </Panel>
        </div>
        <div className="col-span-3">
          <Panel title="Control, gaps and cost by nationality group (descriptive; synthetic data)" pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-2">
              <table className="data-table">
                <thead>
                  <tr><th>Nationality</th><th>Patients</th><th>Mean HbA1c</th><th>% controlled</th><th>Mean gaps</th><th>Mean cost</th></tr>
                </thead>
                <tbody>
                  {eq.map((e) => (
                    <tr key={e.nationality} className={`row-pick ${dashFilter.nationality === e.nationality ? 'picked' : ''}`}
                      onClick={() => toggleFilter('nationality', e.nationality)}>
                      <td className="font-bold" style={{ color: 'var(--text)' }}>{e.nationality}</td>
                      <td>{e.patients.toLocaleString()}</td>
                      <td style={{ color: e.mean_hba1c > 7.5 ? 'var(--red)' : 'var(--text-md)' }}>{e.mean_hba1c}%</td>
                      <td>{e.pct_controlled}%</td>
                      <td>{e.mean_gaps}</td>
                      <td>QAR {Math.round(e.mean_cost).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
