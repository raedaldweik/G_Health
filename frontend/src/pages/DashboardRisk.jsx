import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { getDashboard } from '../services/api';
import DynamicChart, { PALETTE } from '../components/DynamicChart';
import FilterBar from '../components/FilterBar';
import { KpiStrip, Panel, Spinner } from '../components/ui';
import { useApp } from '../context/AppContext';
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine,
} from 'recharts';

const HIGH_RISK = 0.12;   // the model's High band starts here (the operating threshold)

/** Dashboard 3: the machine-learning layer, governed and explainable. */
export default function DashboardRisk() {
  const { dashFilter, toggleFilter } = useApp();
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const [card, setCard] = useState(null);
  useEffect(() => {
    let alive = true;
    setBusy(true);
    getDashboard('risk', dashFilter).then((r) => { if (alive) { setD(r); setBusy(false); } })
      .catch((e) => { if (alive) { setErr(e.message); setBusy(false); } });
    return () => { alive = false; };
  }, [dashFilter]);
  useEffect(() => {
    if (!card) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setCard(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [card]);
  if (err) return <div className="p-8 text-[13px]" style={{ color: 'var(--red)' }}>Dashboard unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const drivers = d.top_drivers.slice(0, 8).map((t) => ({ feature: t.feature, gain: t.gain }));
  const calib = d.calibration.map((c) => ({
    decile: `D${c.decile}`,
    Predicted: +(c.mean_predicted * 100).toFixed(1),
    Observed: +(c.observed_rate * 100).toFixed(1),
  }));
  const sample = d.segments.scatter_sample || [];
  const segNames = [...new Set(sample.map((s) => s.segment))];
  const bands = Object.entries(d.band_distribution).map(([band, patients]) => ({ band, patients }));
  const costs = sample.map((s) => s.annual_cost_qar).sort((a, b) => a - b);
  const medianCost = costs.length ? costs[Math.floor(costs.length / 2)] : 0;
  const maxCost = costs.length ? costs[costs.length - 1] : 0;
  const prof = d.risk_profiles;

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5" style={{ opacity: busy ? 0.75 : 1, transition: 'opacity 0.2s' }}>
      <div className="flex items-end justify-between gap-4 shrink-0 px-1">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Deterioration Risk
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
            Who is likely to deteriorate in the next 12 months, why, and how the model compares with the registry's rule-based tier. Four deployed models with governance cards.
          </p>
        </div>
        <FilterBar info={d.filter} />
      </div>

      <KpiStrip items={[
        { icon: 'gauge', tone: 'teal', label: `AUC on synthetic held-out data (baseline rule-based score ${d.legacy_auc})`, value: d.auc,
          trend: `+${((d.auc - d.legacy_auc) * 100).toFixed(0)}pts · methodology, not clinical validation`, trendDir: 'up' },
        { icon: 'alert', tone: 'red', label: 'Model-expected deterioration events, 12 months (sum of predicted risk)',
          value: Math.round(d.expected_events_12m).toLocaleString() },
        ...bands.map((b, i) => ({
          icon: 'activity', tone: ['green', 'sand', 'amber', 'maroon'][i] || 'teal',
          label: `Model band: ${b.band}`, value: b.patients.toLocaleString(),
        })),
      ]} />

      <div className="flex-1 grid grid-cols-6 grid-rows-2 gap-2.5 min-h-0">
        <div className="col-span-2">
          <Panel title="What drives risk: global feature importance (gain)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'feature', data: drivers,
              yKeys: [{ key: 'gain', label: 'Importance (gain)' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Calibration: predicted vs observed by risk decile">
            <DynamicChart bare spec={{
              type: 'line', xKey: 'decile', data: calib,
              yKeys: [{ key: 'Predicted', label: 'Mean predicted %' },
                      { key: 'Observed', label: 'Observed event %' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Who deteriorates: high-risk vs low-risk profile (top vs bottom decile)" pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-2">
              {prof?.high_risk ? (
                <table className="data-table">
                  <thead><tr><th></th><th style={{ color: 'var(--red)' }}>High risk</th><th style={{ color: 'var(--green)' }}>Low risk</th></tr></thead>
                  <tbody>
                    {[
                      ['Model 12-month risk', (x) => `${x.mean_risk_pct}%`],
                      ['Mean age', (x) => x.mean_age],
                      ['Mean HbA1c', (x) => `${x.mean_hba1c}%`],
                      ['Years since diagnosis', (x) => x.mean_years_since_dx],
                      ['Mean BMI', (x) => x.mean_bmi],
                      ['Mean eGFR', (x) => x.mean_egfr],
                      ['Retinopathy', (x) => `${x.pct_retinopathy}%`],
                      ['Neuropathy', (x) => `${x.pct_neuropathy}%`],
                      ['Chronic kidney disease', (x) => `${x.pct_ckd}%`],
                      ['On insulin', (x) => `${x.pct_on_insulin}%`],
                      ['On SGLT2i / GLP-1 RA', (x) => `${x.pct_on_sglt2_glp1}%`],
                      ['Adherence (PDC)', (x) => `${Math.round(x.mean_adherence_pdc * 100)}%`],
                      ['HbA1c overdue', (x) => `${x.pct_hba1c_overdue}%`],
                      ['Admissions per 12 months', (x) => x.mean_admissions_12mo],
                      ['Annual cost', (x) => `QAR ${x.mean_cost_qar.toLocaleString()}`],
                      ['Top nationalities', (x) => x.top_nationalities.map((n) => n.nationality).join(', ')],
                    ].map(([k, f]) => (
                      <tr key={k}>
                        <td className="font-semibold" style={{ color: 'var(--text-md)' }}>{k}</td>
                        <td className="font-bold" style={{ color: 'var(--text)' }}>{f(prof.high_risk)}</td>
                        <td style={{ color: 'var(--text-md)' }}>{f(prof.low_risk)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-[11px] py-3" style={{ color: 'var(--text-dim)' }}>{prof?.method || 'Not enough patients in the current filter for a decile profile.'}</p>
              )}
            </div>
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Model registry: governance cards" pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-3 space-y-2">
              {d.model_cards.map((c) => (
                <div key={c.model_id} className="rounded-lg px-3 py-2.5 cursor-pointer transition-all hover:shadow-md"
                  style={{ border: '1px solid rgba(138,21,56,0.12)', background: 'rgba(255,255,255,0.35)' }}
                  onClick={() => setCard(c)}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[11.5px] font-bold" style={{ color: 'var(--text)' }}>{c.name}</span>
                    <span className="badge badge-blue">v{c.version}</span>
                    {c.model_id === 'complication_risk' && (
                      <span className="badge badge-green">AUC {c.metrics.auc}</span>
                    )}
                  </div>
                  <p className="text-[10px] mt-1" style={{ color: 'var(--text-dim)' }}>
                    {c.framework} · trained {c.trained}
                  </p>
                  <p className="text-[10px] mt-0.5 leading-snug" style={{ color: 'var(--text-md)' }}>{c.task}</p>
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <div className="col-span-2">
          <Panel title="Population segments: 12-month risk vs annual cost (one dot per patient)"
            right={<span className="text-[9.5px]" style={{ color: 'var(--text-faint)' }}>click a segment to filter</span>}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 14, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgba(15,23,42,0.07)" />
                <XAxis dataKey="risk_prob" type="number" name="12-mo risk" domain={[0, 1]}
                  tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false}
                  tickFormatter={(v) => `${Math.round(v * 100)}%`}
                  axisLine={{ stroke: 'rgba(15,23,42,0.15)' }} />
                <YAxis dataKey="annual_cost_qar" type="number" name="Annual cost"
                  tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} width={52}
                  tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <ReferenceLine x={HIGH_RISK} stroke="rgba(155,28,70,0.5)" strokeDasharray="4 3"
                  label={{ value: 'High band from 12%', position: 'insideBottomRight', fontSize: 9.5, fill: '#9b1c46', dy: -14 }} />
                <ReferenceLine y={medianCost} stroke="rgba(15,23,42,0.35)" strokeDasharray="4 3"
                  label={{ value: `median cost QAR ${Math.round(medianCost / 1000)}k`, position: 'insideBottomRight', fontSize: 9.5, fill: '#64748b' }} />
                <ReferenceLine y={maxCost * 0.93} stroke="none"
                  label={{ value: 'costly today, lower risk', position: 'insideLeft', fontSize: 9.5, fill: '#94a3b8' }} />
                <ReferenceLine y={medianCost * 0.55} stroke="none"
                  label={{ value: "high risk, tomorrow's cost", position: 'insideRight', fontSize: 9.5, fill: '#94a3b8' }} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }}
                  formatter={(v, name) => name === 'Annual cost'
                    ? [`QAR ${Number(v).toLocaleString()}`, name]
                    : [`${(v * 100).toFixed(0)}%`, '12-mo risk']} />
                <Legend wrapperStyle={{ fontSize: 10.5, cursor: 'pointer' }} iconSize={9}
                  onClick={(e) => toggleFilter('segment', e.value)} />
                {segNames.map((s, i) => (
                  <Scatter key={s} name={s} fill={PALETTE[i % PALETTE.length]}
                    fillOpacity={dashFilter.segment && dashFilter.segment !== s ? 0.15 : 0.55}
                    data={sample.filter((r) => r.segment === s)} onClick={() => toggleFilter('segment', s)} />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Highest model-risk patients (prioritised work list)" pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-2">
              <table className="data-table">
                <thead><tr><th>Patient</th><th>Age</th><th>HbA1c</th><th>Risk</th><th>Gaps</th></tr></thead>
                <tbody>
                  {d.highest_risk.map((p) => (
                    <tr key={p.patient_id}>
                      <td className="font-bold" style={{ color: 'var(--text)' }}>{p.patient_id}</td>
                      <td>{p.age}</td>
                      <td>{p.hba1c_latest ?? 'n/a'}</td>
                      <td><span className="badge badge-red">{Math.round(p.risk_prob * 100)}%</span></td>
                      <td>{p.care_gap_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      </div>

      {/* Model card modal: rendered into document.body so the glass panels' backdrop filters
          cannot capture the fixed positioning. */}
      {card && createPortal(
        <div className="fixed inset-0 z-[300] flex items-center justify-center p-6" onClick={() => setCard(null)}
          style={{ background: 'rgba(10,22,40,0.45)', backdropFilter: 'blur(4px)' }}>
          <div className="glass-card w-full max-w-[560px] max-h-[80vh] overflow-y-auto p-6 animate-slide-up"
            onClick={(e) => e.stopPropagation()} style={{ background: 'rgba(255,255,255,0.97)' }}>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h2 className="text-[15px] font-extrabold" style={{ color: 'var(--text)' }}>{card.name}</h2>
              <span className="badge badge-blue">v{card.version}</span>
              <button type="button" className="ml-auto text-[11px] font-bold" style={{ color: 'var(--text-dim)' }} onClick={() => setCard(null)}>Close</button>
            </div>
            <p className="text-[11px] mb-3" style={{ color: 'var(--text-dim)' }}>{card.framework} · trained {card.trained}</p>
            {[['Task', card.task], ['Training data', card.training_data],
              ['Intended use', card.intended_use], ['Clinical constraints', card.constraints],
              ['Limitations', card.limitations],
              ['On Google Cloud', card.phase2]].filter(([, v]) => v).map(([k, v]) => (
              <div key={k} className="mb-2.5">
                <p className="text-[9.5px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-dim)' }}>{k}</p>
                <p className="text-[12px] leading-relaxed" style={{ color: 'var(--text-md)' }}>{v}</p>
              </div>
            ))}
            <div className="mb-1">
              <p className="text-[9.5px] font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--text-dim)' }}>Features</p>
              <div className="flex flex-wrap gap-1">
                {(card.features || []).map((f) => (
                  <span key={f} className="text-[9.5px] px-1.5 py-0.5 rounded font-mono"
                    style={{ background: 'rgba(15,23,42,0.05)', color: 'var(--text-md)' }}>{f}</span>
                ))}
              </div>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
