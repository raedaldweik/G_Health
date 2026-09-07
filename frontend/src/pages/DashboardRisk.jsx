import { useEffect, useState } from 'react';
import { getDashboard } from '../services/api';
import DynamicChart, { PALETTE } from '../components/DynamicChart';
import { KpiTile, Panel, Spinner } from '../components/ui';
import {
  ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts';

/** Dashboard 3 — Risk & Models: the machine-learning layer, governed and explainable. */
export default function DashboardRisk() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [card, setCard] = useState(null);
  useEffect(() => { getDashboard('risk').then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="p-8 text-[13px]" style={{ color: 'var(--red)' }}>Dashboard unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const drivers = d.top_drivers.slice(0, 8).map((t) => ({ feature: t.feature, gain: t.gain }));
  const calib = d.calibration.map((c) => ({
    decile: `D${c.decile}`,
    Predicted: +(c.mean_predicted * 100).toFixed(1),
    Observed: +(c.observed_rate * 100).toFixed(1),
  }));
  const segNames = [...new Set(d.segments.scatter_sample.map((s) => s.segment))];
  const bands = Object.entries(d.band_distribution).map(([band, patients]) => ({ band, patients }));

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5">
      <div className="flex items-end justify-between shrink-0 px-1">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Risk &amp; Models — the machine-learning layer
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
            Four deployed models with governance cards. Phase 2: BigQuery ML → Vertex Model Registry → online endpoint, scored through the official /mcp/predict toolset.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-6 gap-2.5 shrink-0">
        <KpiTile label="Risk model AUC" value={d.auc} sub={`vs ${d.legacy_auc} legacy registry score`} />
        <KpiTile label="Expected events (12 mo)" value={Math.round(d.expected_events_12m).toLocaleString()} accent="red" />
        {bands.map((b) => (
          <KpiTile key={b.band} label={`Model band · ${b.band}`} value={b.patients.toLocaleString()} />
        ))}
      </div>

      <div className="flex-1 grid grid-cols-6 grid-rows-2 gap-2.5 min-h-0">
        <div className="col-span-2">
          <Panel title="What drives risk — global feature importance (gain)">
            <DynamicChart bare spec={{
              type: 'bar', xKey: 'feature', data: drivers,
              yKeys: [{ key: 'gain', label: 'Importance (gain)' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2">
          <Panel title="Calibration — predicted vs observed by risk decile">
            <DynamicChart bare spec={{
              type: 'line', xKey: 'decile', data: calib,
              yKeys: [{ key: 'Predicted', label: 'Mean predicted %' },
                      { key: 'Observed', label: 'Observed event %' }],
            }} />
          </Panel>
        </div>
        <div className="col-span-2 row-span-2">
          <Panel title="Model registry — governance cards" pad={false}>
            <div className="overflow-y-auto h-full px-3 pb-3 space-y-2">
              {d.model_cards.map((c) => (
                <div key={c.model_id} className="rounded-lg px-3 py-2.5 cursor-pointer transition-all hover:shadow-md"
                  style={{ border: '1px solid rgba(26,115,232,0.12)', background: 'rgba(255,255,255,0.35)' }}
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
          <Panel title="Population segments — model risk vs annual cost">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgba(15,23,42,0.07)" />
                <XAxis dataKey="risk_prob" type="number" name="12-mo risk"
                  tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false}
                  tickFormatter={(v) => `${Math.round(v * 100)}%`}
                  axisLine={{ stroke: 'rgba(15,23,42,0.15)' }} />
                <YAxis dataKey="annual_cost_qar" type="number" name="Annual cost"
                  tick={{ fontSize: 10, fill: '#64748b' }} tickLine={false} axisLine={false} width={52}
                  tickFormatter={(v) => `${Math.round(v / 1000)}k`} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }}
                  formatter={(v, name) => name === 'Annual cost'
                    ? [`QAR ${Number(v).toLocaleString()}`, name]
                    : [`${(v * 100).toFixed(0)}%`, '12-mo risk']} />
                <Legend wrapperStyle={{ fontSize: 10.5 }} iconSize={9} />
                {segNames.map((s, i) => (
                  <Scatter key={s} name={s} fill={PALETTE[i % PALETTE.length]} fillOpacity={0.55}
                    data={d.segments.scatter_sample.filter((r) => r.segment === s)} />
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
                      <td>{p.hba1c_latest ?? '—'}</td>
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

      {/* Model card modal */}
      {card && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center p-6" onClick={() => setCard(null)}
          style={{ background: 'rgba(10,22,40,0.45)', backdropFilter: 'blur(4px)' }}>
          <div className="glass-card w-full max-w-[560px] max-h-[80vh] overflow-y-auto p-6 animate-slide-up"
            onClick={(e) => e.stopPropagation()} style={{ background: 'rgba(255,255,255,0.96)' }}>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h2 className="text-[15px] font-extrabold" style={{ color: 'var(--text)' }}>{card.name}</h2>
              <span className="badge badge-blue">v{card.version}</span>
            </div>
            <p className="text-[11px] mb-3" style={{ color: 'var(--text-dim)' }}>{card.framework} · trained {card.trained}</p>
            {[['Task', card.task], ['Training data', card.training_data],
              ['Intended use', card.intended_use], ['Limitations', card.limitations],
              ['Phase 2 on Google Cloud', card.phase2]].map(([k, v]) => (
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
        </div>
      )}
    </div>
  );
}
