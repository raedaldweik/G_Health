import { useEffect, useState } from 'react';
import { getDashboard } from '../services/api';
import DynamicChart from '../components/DynamicChart';
import { KpiStrip, Panel, Spinner } from '../components/ui';

/** Dashboard 4 — Cost & Equity: where the riyal goes, and who the system is missing. */
export default function DashboardCost() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { getDashboard('cost').then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="p-8 text-[13px]" style={{ color: 'var(--red)' }}>Dashboard unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const cc = d.concentration;
  const eq = d.equity;
  const gapPP = (eq[0].mean_hba1c - eq[eq.length - 1].mean_hba1c).toFixed(2);

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5">
      <div className="shrink-0 px-1">
        <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
          Cost &amp; Equity — where the riyal goes, and who we're missing
        </h1>
        <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
          Spend concentration is a targeting opportunity; the equity gradient tracks access, not biology — National Health Strategy pillar alignment.
        </p>
      </div>

      <KpiStrip items={[
        { icon: 'coins', tone: 'gold', label: 'Total annual cost',
          value: (cc.total_annual_cost_qar / 1e6).toFixed(1), suffix: 'M QAR' },
        { icon: 'users', tone: 'sand', label: 'Top 10% of patients — share of spend',
          value: `${cc.top10pct_share_pct}%` },
        { icon: 'alert', tone: 'red', label: `Equity spread — ${eq[0].nationality} vs ${eq[eq.length - 1].nationality}`,
          value: gapPP, suffix: 'pp' },
        { icon: 'activity', tone: 'violet', label: 'Costliest segment',
          value: [...d.segments].sort((a, b) => b.total_cost - a.total_cost)[0]?.segment ?? '—' },
      ]} />

      <div className="flex-1 grid grid-cols-6 grid-rows-2 gap-2.5 min-h-0">
        <div className="col-span-2">
          <Panel title="Cost concentration — cumulative share of spend">
            <DynamicChart bare spec={{
              type: 'area', xKey: 'patients',
              data: cc.deciles.map((x) => ({ patients: `${x.top_pct_patients}%`, share: x.pct_of_spend })),
              yKeys: [{ key: 'share', label: 'Cumulative % of spend' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Annual spend by population segment">
            <DynamicChart bare spec={{
              type: 'pie', xKey: 'segment',
              data: [...d.segments].sort((a, b) => b.total_cost - a.total_cost)
                .map((s) => ({ segment: s.segment, spend: +(s.total_cost / 1e6).toFixed(2) })),
              yKeys: [{ key: 'spend', label: 'QAR (M)' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Total spend by facility (QAR M)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'facility',
              data: d.by_facility.slice(0, 10).map((f) => ({
                facility: f.facility.replace(' Health Center', '').replace(' Hospital', ' H.'),
                spend: f.total_qar_m,
              })),
              yKeys: [{ key: 'spend', label: 'QAR (M)' }],
            }} />
          </Panel>
        </div>

        <div className="col-span-3">
          <Panel title="Equity — mean HbA1c by nationality (the access gradient)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'nationality',
              data: eq.map((e) => ({ nationality: e.nationality, HbA1c: e.mean_hba1c })),
              yKeys: [{ key: 'HbA1c', label: 'Mean HbA1c %' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-3">
          <Panel title="Equity detail — control, gaps and cost by nationality" pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-2">
              <table className="data-table">
                <thead>
                  <tr><th>Nationality</th><th>Patients</th><th>Mean HbA1c</th><th>% controlled</th><th>Mean gaps</th><th>Mean cost</th></tr>
                </thead>
                <tbody>
                  {eq.map((e) => (
                    <tr key={e.nationality}>
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
