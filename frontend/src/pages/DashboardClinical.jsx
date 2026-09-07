import { useEffect, useState } from 'react';
import { getDashboard } from '../services/api';
import DynamicChart from '../components/DynamicChart';
import { Donut3D } from '../components/Chart3D';
import { Panel, Spinner } from '../components/ui';

/** Dashboard 2 — Clinical quality: where care falls short of the guideline, measure by measure. */
export default function DashboardClinical() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { getDashboard('clinical').then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="p-8 text-[13px]" style={{ color: 'var(--red)' }}>Dashboard unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const bp = d.bp_control;
  const bpTotal = bp.controlled + bp.uncontrolled;

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5">
      <div className="shrink-0 px-1">
        <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
          Clinical Quality — where care falls short
        </h1>
        <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
          HEDIS-style measures computed live from the HIE by the population-health MCP server. Every ❌ is a work list, not a statistic.
        </p>
      </div>

      <div className="flex-1 grid grid-cols-6 grid-rows-2 gap-2.5 min-h-0">
        <div className="col-span-3 row-span-2">
          <Panel title="Quality measure scorecard — rate vs target" pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-3">
              <table className="data-table">
                <thead>
                  <tr><th>Measure</th><th>Rate</th><th style={{ minWidth: 130 }}>vs target</th><th>Gap</th></tr>
                </thead>
                <tbody>
                  {d.quality_measures.map((m) => (
                    <tr key={m.measure_id}>
                      <td style={{ whiteSpace: 'normal', minWidth: 170 }}>
                        <span className="font-bold" style={{ color: 'var(--text)' }}>{m.measure_id}</span>
                        <div className="text-[10px]" style={{ color: 'var(--text-dim)' }}>{m.name}</div>
                      </td>
                      <td className="font-extrabold" style={{ color: m.met ? 'var(--green)' : 'var(--red)' }}>
                        {m.rate_pct}%
                      </td>
                      <td>
                        <div className="relative h-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(15,23,42,0.07)' }}>
                          <div className="absolute inset-y-0 left-0 rounded-full"
                            style={{ width: `${Math.min(m.rate_pct, 100)}%`, background: m.met ? 'var(--green)' : '#9b1c46' }} />
                          <div className="absolute inset-y-0 w-[2px]" style={{ left: `${m.target_pct}%`, background: 'var(--text-dim)' }} />
                        </div>
                        <div className="text-[9px] mt-0.5" style={{ color: 'var(--text-faint)' }}>target {m.target_pct}%</div>
                      </td>
                      <td>
                        {m.met
                          ? <span className="badge badge-green">met</span>
                          : <span className="badge badge-red">{m.gap_patients}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        <div className="col-span-2">
          <Panel title="Glycaemic control distribution (diabetes cohort)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'band', data: d.control_distribution,
              yKeys: [{ key: 'patients', label: 'Patients' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-1">
          <Panel title="BP control (hypertension)">
            <Donut3D
              data={[{ label: 'Controlled', value: bp.controlled, ramp: 3 },
                     { label: 'Uncontrolled', value: bp.uncontrolled, ramp: 6 }]}
              centerValue={`${((bp.controlled / bpTotal) * 100).toFixed(0)}%`}
              centerLabel="controlled <140/90"
              valueFormatter={(v) => v.toLocaleString()} showLegend={true} />
          </Panel>
        </div>

        <div className="col-span-2">
          <Panel title="Open care gaps by type">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'gap',
              data: d.care_gaps.map((g) => ({ gap: g.gap_label.split(' (')[0].slice(0, 24), patients: g.patients })),
              yKeys: [{ key: 'patients', label: 'Patients' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-1">
          <Panel title="Worst gap loads by facility" pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-2">
              {d.gap_facility_matrix.rows
                .map((r) => ({ f: r.facility, total: d.gap_facility_matrix.gap_keys.reduce((s, k) => s + (r[k] || 0), 0) }))
                .sort((a, b) => b.total - a.total).slice(0, 7)
                .map((r, i) => (
                  <div key={i} className="flex items-center justify-between py-1.5 border-b border-[rgba(15,23,42,0.05)] last:border-0">
                    <span className="text-[10px] font-semibold pr-1 leading-tight" style={{ color: 'var(--text-md)' }}>
                      {r.f.replace(' Health Center', '').replace(' Hospital', ' H.')}
                    </span>
                    <span className="badge badge-amber">{r.total}</span>
                  </div>
                ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
