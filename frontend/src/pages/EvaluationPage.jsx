import { Fragment, useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ComposedChart, Bar, ReferenceLine,
} from 'recharts';
import {
  getModelEval, getAgentEval, runAgentEval, getAgentEvalStatus, getLlmSelection, getGovernance,
} from '../services/api';
import { Bar3D } from '../components/Chart3D';
import { AgentChip, KpiStrip, Panel, Spinner } from '../components/ui';

/*
 * AI Evaluation, the "prove it" tab.
 *   Model   · held-out discrimination, calibration, threshold economics, subgroup fairness
 *   Agents  · golden evalset run through the real graph: trajectory, groundedness, safety, faithfulness, cost
 *   LLM     · why this model, why not Pro everywhere, why specialists beat one fat agent (measured in tokens)
 *   Govern  · the control list, implemented here vs delivered by Google Cloud
 * Every number here is computed on request from data the model never trained on.
 */

const MAROON = '#9b1c46';
const GOLD = '#b8862e';
const VIOLET = '#6d4fa8';
const GREEN = '#3a8e5a';

const VIEWS = [
  ['model', 'Risk model'],
  ['agents', 'Agent evalset'],
  ['llm', 'LLM & cost'],
  ['governance', 'Governance'],
];

const pct = (v, d = 1) => (v == null ? 'n/a' : `${(v * 100).toFixed(d)}%`);
/** Linear interpolation of a monotone {x,y} curve at x (curves from the backend are sorted by x). */
function interp(curve, x) {
  if (!curve.length) return 0;
  if (x <= curve[0].x) return curve[0].y;
  for (let i = 1; i < curve.length; i++) {
    if (x <= curve[i].x) {
      const a = curve[i - 1], b = curve[i];
      return b.x === a.x ? Math.max(a.y, b.y) : a.y + (b.y - a.y) * (x - a.x) / (b.x - a.x);
    }
  }
  return curve[curve.length - 1].y;
}
const num = (v, d = 3) => (v == null ? 'n/a' : Number(v).toFixed(d));

function Tick({ children }) {
  return <span className="font-extrabold" style={{ color: GREEN }}>{children ?? '✓'}</span>;
}
function Cross({ children }) {
  return <span className="font-extrabold" style={{ color: 'var(--red)' }}>{children ?? '✗'}</span>;
}

function TipBox({ active, payload, label, fmt }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg px-2.5 py-1.5 text-[10.5px] shadow-lg"
      style={{ background: 'rgba(255,255,255,0.96)', border: '1px solid rgba(138,21,56,0.18)' }}>
      <p className="font-bold mb-0.5" style={{ color: 'var(--text)' }}>{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>{p.name}: <b>{fmt ? fmt(p.value) : p.value}</b></p>
      ))}
    </div>
  );
}

/* ───────────────────────────── 1. Model evaluation ───────────────────────────── */
function ModelView() {
  const [t, setT] = useState(0.12);
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { getModelEval(t).then(setD).catch((e) => setErr(e.message)); }, [t]);
  if (err) return <div className="p-6 text-[12px]" style={{ color: 'var(--red)' }}>Model evaluation unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const xs = [...new Set([...d.roc, ...d.roc_legacy].map((p) => p.x))].sort((a, b) => a - b);
  const roc = xs.map((x) => ({ fpr: +(x * 100).toFixed(2), model: +(interp(d.roc, x) * 100).toFixed(1),
    legacy: +(interp(d.roc_legacy, x) * 100).toFixed(1), chance: +(x * 100).toFixed(1) }));
  const pr = [...d.pr].sort((a, b) => a.x - b.x).map((p) => ({ recall: +(p.x * 100).toFixed(1), precision: +(p.y * 100).toFixed(1) }));
  const calib = d.calibration.map((c) => ({ decile: `D${c.decile}`, Predicted: +(c.mean_predicted * 100).toFixed(1),
    Observed: +(c.observed_rate * 100).toFixed(1) }));
  const op = d.operating;
  const brierGain = d.brier_baseline ? (1 - d.brier / d.brier_baseline) : null;
  const aucDelta = ((d.auc - d.legacy_auc) * 100).toFixed(1);

  return (
    <div className="flex flex-col gap-2.5">
      <KpiStrip items={[
        { icon: 'gauge', tone: 'maroon', label: 'AUC: held-out (legacy registry score)', value: d.auc.toFixed(3),
          trend: `+${aucDelta} pts vs ${d.legacy_auc.toFixed(3)}`, trendDir: 'up' },
        { icon: 'activity', tone: 'gold', label: 'Average precision (event rate)', value: d.average_precision.toFixed(3),
          trend: `base ${pct(d.event_rate)}`, trendDir: 'flat' },
        { icon: 'check', tone: 'green', label: 'Brier score (lower is better)', value: d.brier.toFixed(3),
          trend: `${(brierGain * 100).toFixed(0)}% better than prevalence`, trendDir: 'up' },
        { icon: 'heart', tone: 'violet', label: 'Calibration slope (1.0 = perfect)', value: num(d.calibration_slope, 2) },
        { icon: 'users', tone: 'sand', label: 'Held-out patients never seen in training', value: d.test_rows.toLocaleString(),
          trend: `${d.events} events`, trendDir: 'flat' },
      ]} />

      <div className="grid grid-cols-12 gap-2.5" style={{ minHeight: 300 }}>
        <div className="col-span-5" style={{ height: 300 }}>
          <Panel title="ROC: model vs the registry's rule-based tier">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={roc} margin={{ top: 8, right: 12, left: -18, bottom: 2 }}>
                <CartesianGrid stroke="rgba(15,23,42,0.06)" />
                <XAxis dataKey="fpr" type="number" domain={[0, 100]} tick={{ fontSize: 9.5, fill: '#64748b' }} unit="%" tickCount={6} />
                <YAxis type="number" domain={[0, 100]} tick={{ fontSize: 9.5, fill: '#64748b' }} unit="%" tickCount={6} />
                <Tooltip content={<TipBox fmt={(v) => `${v}%`} />} labelFormatter={(l) => `False-positive rate ${l}%`} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Line type="monotone" dataKey="chance" name="Chance" stroke="#94a3b8" strokeDasharray="4 4" dot={false} strokeWidth={1} isAnimationActive={false} />
                <Line type="monotone" dataKey="legacy" name={`Legacy score · AUC ${d.legacy_auc.toFixed(3)}`} stroke={GOLD} dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="model" name={`XGBoost · AUC ${d.auc.toFixed(3)}`} stroke={MAROON} dot={false} strokeWidth={2.6} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>
        </div>

        <div className="col-span-3" style={{ height: 300 }}>
          <Panel title="Precision–recall (rare event, 10%)">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={pr} margin={{ top: 8, right: 12, left: -18, bottom: 2 }}>
                <CartesianGrid stroke="rgba(15,23,42,0.06)" />
                <XAxis dataKey="recall" type="number" domain={[0, 100]} tick={{ fontSize: 9.5, fill: '#64748b' }} unit="%" tickCount={6} />
                <YAxis type="number" domain={[0, 100]} tick={{ fontSize: 9.5, fill: '#64748b' }} unit="%" tickCount={6} />
                <Tooltip content={<TipBox fmt={(v) => `${v}%`} />} labelFormatter={(l) => `Recall ${l}%`} />
                <ReferenceLine y={+(d.event_rate * 100).toFixed(1)} stroke={GOLD} strokeDasharray="4 4"
                  label={{ value: 'prevalence', fontSize: 9, fill: GOLD, position: 'insideTopRight' }} />
                <Line type="monotone" dataKey="precision" name="Precision" stroke={VIOLET} dot={false} strokeWidth={2.4} />
              </LineChart>
            </ResponsiveContainer>
          </Panel>
        </div>

        <div className="col-span-4" style={{ height: 300 }}>
          <Panel title="Calibration: predicted vs observed by risk decile">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={calib} margin={{ top: 8, right: 12, left: -18, bottom: 2 }}>
                <CartesianGrid stroke="rgba(15,23,42,0.06)" vertical={false} />
                <XAxis dataKey="decile" tick={{ fontSize: 9.5, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 9.5, fill: '#64748b' }} unit="%" />
                <Tooltip content={<TipBox fmt={(v) => `${v}%`} />} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Bar dataKey="Observed" fill={MAROON} radius={[4, 4, 0, 0]} fillOpacity={0.85} />
                <Line type="monotone" dataKey="Predicted" stroke={GOLD} strokeWidth={2.4} dot={{ r: 3, fill: GOLD }} />
              </ComposedChart>
            </ResponsiveContainer>
          </Panel>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-2.5">
        <div className="col-span-7">
          <Panel title="Threshold economics: where do you draw the line?"
            right={
              <div className="flex items-center gap-2 text-[10px]" style={{ color: 'var(--text-dim)' }}>
                <span>Operating threshold</span>
                <input type="range" min={0.04} max={0.4} step={0.01} value={t} onChange={(e) => setT(+e.target.value)}
                  style={{ accentColor: MAROON, width: 140 }} />
                <b style={{ color: 'var(--brand)', minWidth: 34 }}>{pct(t, 0)}</b>
              </div>
            }>
            <div className="px-1 pb-1">
              <div className="grid grid-cols-4 gap-2 mb-2">
                {[['True positives', op.tp, GREEN, 'events caught'], ['False positives', op.fp, GOLD, 'reviewed, no event'],
                  ['False negatives', op.fn, 'var(--red)', 'events missed'], ['True negatives', op.tn, '#64748b', 'correctly left alone']].map(([k, v, c, sub]) => (
                  <div key={k} className="rounded-lg px-2.5 py-2" style={{ background: 'rgba(255,255,255,0.55)', border: '1px solid var(--hairline)' }}>
                    <p className="text-[8.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-faint)' }}>{k}</p>
                    <p className="text-[20px] font-extrabold leading-none mt-0.5" style={{ color: c }}>{v}</p>
                    <p className="text-[9px] mt-0.5" style={{ color: 'var(--text-dim)' }}>{sub}</p>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-4 text-[10.5px] mb-2 px-1" style={{ color: 'var(--text-md)' }}>
                <span>Sensitivity <b style={{ color: 'var(--text)' }}>{pct(op.sensitivity)}</b></span>
                <span>Specificity <b style={{ color: 'var(--text)' }}>{pct(op.specificity)}</b></span>
                <span>PPV <b style={{ color: 'var(--text)' }}>{pct(op.ppv)}</b></span>
                <span>Flagged <b style={{ color: 'var(--text)' }}>{pct(op.flag_rate)}</b> of panel</span>
                <span>Reviews per event found <b style={{ color: 'var(--brand)' }}>{op.nnt_to_find_one_event}</b></span>
              </div>
              <table className="w-full text-[10px]">
                <thead>
                  <tr style={{ color: 'var(--text-faint)' }} className="text-left uppercase tracking-wider">
                    <th className="py-1 font-bold">Threshold</th><th className="font-bold">Flag rate</th><th className="font-bold">Sensitivity</th>
                    <th className="font-bold">Specificity</th><th className="font-bold">PPV</th><th className="font-bold">Reviews / event</th>
                  </tr>
                </thead>
                <tbody>
                  {d.threshold_sweep.map((r) => {
                    const active = Math.abs(r.threshold - t) < 0.005;
                    return (
                      <tr key={r.threshold} style={{ background: active ? 'rgba(138,21,56,0.08)' : 'transparent', color: 'var(--text-md)' }}
                        className="border-t border-[rgba(15,23,42,0.05)]">
                        <td className="py-1 font-bold" style={{ color: active ? 'var(--brand)' : 'var(--text)' }}>≥ {pct(r.threshold, 0)}</td>
                        <td>{pct(r.flag_rate)}</td><td>{pct(r.sensitivity)}</td><td>{pct(r.specificity)}</td><td>{pct(r.ppv)}</td>
                        <td>{r.nnt_to_find_one_event ?? 'n/a'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="text-[9.5px] mt-1.5 px-1" style={{ color: 'var(--text-dim)' }}>
                The model does not choose the threshold; the ministry does. At {pct(t, 0)} a nurse reviews {op.nnt_to_find_one_event} charts to find one
                12-month event; the Very-High band (≥ 25%) needs {d.very_high.nnt_to_find_one_event} but misses {pct(1 - d.very_high.sensitivity, 0)} of events.
              </p>
            </div>
          </Panel>
        </div>

        <div className="col-span-5">
          <Panel title="Subgroup fairness at the operating threshold">
            <div className="px-1 pb-1 overflow-y-auto" style={{ maxHeight: 420 }}>
              {d.subgroups.map((sg) => (
                <div key={sg.dimension} className="mb-2.5">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[9.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-faint)' }}>
                      {sg.dimension === 'nat_group' ? 'Nationality group' : sg.dimension === 'age_band' ? 'Age band' : 'Gender'}
                    </p>
                    <span className={`badge ${sg.tpr_gap > 0.15 ? 'badge-amber' : 'badge-green'}`} style={{ fontSize: 8.5 }}>
                      TPR gap {pct(sg.tpr_gap, 1)} · FPR gap {pct(sg.fpr_gap, 1)}
                    </span>
                  </div>
                  <table className="w-full text-[10px]">
                    <thead>
                      <tr style={{ color: 'var(--text-faint)' }} className="text-left">
                        <th className="font-bold py-0.5">Group</th><th className="font-bold">n</th><th className="font-bold">events</th>
                        <th className="font-bold">AUC</th><th className="font-bold">TPR</th><th className="font-bold">FPR</th><th className="font-bold">Flagged</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sg.rows.map((r) => (
                        <tr key={r.group} className="border-t border-[rgba(15,23,42,0.05)]" style={{ color: r.small_sample ? 'var(--text-faint)' : 'var(--text-md)' }}>
                          <td className="py-0.5 font-semibold">{r.group}{r.small_sample && <span className="ml-1 text-[8px] font-bold" style={{ color: 'var(--amber)' }}>small n</span>}</td>
                          <td>{r.n}</td><td>{r.events}</td><td>{num(r.auc, 3)}</td><td>{pct(r.tpr, 0)}</td><td>{pct(r.fpr, 0)}</td><td>{pct(r.flag_rate, 0)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
              <p className="text-[9.5px]" style={{ color: 'var(--text-dim)' }}>
                Gaps are computed only across groups with ≥ {d.subgroups[0]?.min_events} events; smaller groups are shown but not judged.
                The age gap is expected: event prevalence is {pct(d.subgroups.find((s) => s.dimension === 'age_band')?.rows.find((r) => r.group === '65+')?.prevalence, 0)} over 65 versus
                {' '}{pct(d.subgroups.find((s) => s.dimension === 'age_band')?.rows.find((r) => r.group === '<50')?.prevalence, 0)} under 50, so a single threshold catches more of the older group.
                On Google Cloud these rows are re-run monthly (a BigQuery drift job, Model Monitoring where offered in region) and alert on drift.
              </p>
            </div>
          </Panel>
        </div>
      </div>

      <div className="glass-card px-4 py-2.5 text-[10.5px]" style={{ color: 'var(--text-md)' }}>
        <b style={{ color: 'var(--text)' }}>Method.</b> {d.method} Legacy score = the registry's rule-based points tier (age, HbA1c, prior admission, blood pressure) rescaled to [0,1].
        Feature importance and SHAP-style per-patient contributions live on the Risk &amp; Models dashboard.
      </div>
    </div>
  );
}

/* ───────────────────────────── 2. Agent evaluation ───────────────────────────── */
function AgentsView() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [status, setStatus] = useState(null);
  const [mode, setMode] = useState('auto');
  const [open, setOpen] = useState(null);

  const load = () => getAgentEval().then((x) => { setD(x); setStatus(x.status); }).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!status?.running) return undefined;
    const id = setInterval(() => getAgentEvalStatus().then((s) => { setStatus(s); if (!s.running) load(); }).catch(() => {}), 1200);
    return () => clearInterval(id);
  }, [status?.running]);

  if (err) return <div className="p-6 text-[12px]" style={{ color: 'var(--red)' }}>Agent evaluation unavailable: {err}</div>;
  if (!d) return <Spinner />;

  const r = d.results;
  const cases = d.evalset?.cases || [];
  const rows = r?.results || [];
  const byId = Object.fromEntries(rows.map((x) => [x.id, x]));
  const running = !!status?.running;
  const progress = running && status.total ? Math.round((status.progress / status.total) * 100) : 0;
  const live = r && r.mode === 'live';

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-center justify-between gap-3">
        <KpiStrip items={r ? [
          { icon: 'check', tone: r.pass_rate >= 0.9 ? 'green' : 'amber', label: `Cases passed (${r.passed}/${rows.length})`, value: pct(r.pass_rate, 0),
            trend: live && r.cost_per_question_usd != null ? `$${r.cost_per_question_usd.toFixed(4)} / q · p95 ${r.p95_latency_ms} ms` : `p95 ${r.p95_latency_ms} ms`, trendDir: 'flat' },
          { icon: 'activity', tone: 'maroon', label: 'Tool-trajectory recall', value: pct(r.mean_trajectory_recall, 0) },
          { icon: 'heart', tone: 'gold', label: 'Groundedness · citations where required', value: pct(r.groundedness_rate, 0) },
          { icon: 'alert', tone: 'violet', label: 'Action safety · nothing bypassed the queue', value: pct(r.action_safety_rate, 0) },
          { icon: 'gauge', tone: 'sand', label: 'Numeric faithfulness vs ground truth', value: pct(r.faithfulness_rate, 0) },
        ] : [{ icon: 'alert', tone: 'amber', label: 'No results yet: run the evalset', value: 'n/a' }]} />
      </div>

      <div className="grid grid-cols-12 gap-2.5">
        <div className="col-span-8">
          <Panel title={`Golden evalset: ${cases.length} cases through the real agent graph`}
            right={
              <div className="flex items-center gap-2">
                <div className="seg-track" style={{ padding: 2 }}>
                  {[['auto', 'Auto'], ['live', 'Live agent'], ['direct', 'Direct tools']].map(([k, l]) => (
                    <button key={k} className={`seg-pill ${mode === k ? 'active' : ''}`} style={{ fontSize: 10, padding: '4px 9px' }}
                      onClick={() => setMode(k)}>{l}</button>
                  ))}
                </div>
                <button disabled={running} onClick={() => runAgentEval(mode).then(() => setStatus({ running: true, progress: 0, total: cases.length })).catch(() => {})}
                  className="px-3 py-1.5 rounded-lg text-[10.5px] font-bold text-white"
                  style={{ background: running ? '#94a3b8' : 'var(--brand-grad)', boxShadow: running ? 'none' : '0 4px 12px rgba(138,21,56,0.3)' }}>
                  {running ? `Running… ${status.progress}/${status.total}` : 'Run evalset'}
                </button>
              </div>
            }>
            {running && (
              <div className="mx-2 mb-2 h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(138,21,56,0.12)' }}>
                <div className="h-full transition-all" style={{ width: `${progress}%`, background: 'var(--brand-grad)' }} />
              </div>
            )}
            <div className="px-1 overflow-y-auto" style={{ maxHeight: 480 }}>
              <table className="w-full text-[10px]">
                <thead>
                  <tr style={{ color: 'var(--text-faint)' }} className="text-left uppercase tracking-wider">
                    <th className="py-1 font-bold">Case</th><th className="font-bold">Expected tools</th>
                    <th className="font-bold text-center">Traj.</th><th className="font-bold text-center">Grounded</th>
                    <th className="font-bold text-center">Safe</th><th className="font-bold text-center">Faithful</th>
                    <th className="font-bold text-right">Latency</th><th className="font-bold text-right">Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c) => {
                    const x = byId[c.id];
                    const isOpen = open === c.id;
                    return (
                      <Fragment key={c.id}>
                        <tr onClick={() => setOpen(isOpen ? null : c.id)}
                          className="border-t border-[rgba(15,23,42,0.05)] cursor-pointer hover:bg-[rgba(138,21,56,0.04)]"
                          style={{ color: 'var(--text-md)', background: isOpen ? 'rgba(138,21,56,0.05)' : undefined }}>
                          <td className="py-1.5 pr-2" style={{ maxWidth: 260 }}>
                            <p className="font-bold truncate" style={{ color: 'var(--text)' }}>{c.question}</p>
                            <p className="text-[9px]" style={{ color: 'var(--text-faint)' }}>{c.id} · {c.persona}</p>
                          </td>
                          <td className="pr-2">
                            <div className="flex flex-wrap gap-1">
                              {c.expected_tools.map((tname) => {
                                const hit = x ? x.observed_tools?.includes(tname) : null;
                                return <span key={tname} className="px-1.5 py-0.5 rounded font-mono text-[8.5px] font-bold"
                                  style={{ background: hit === false ? 'var(--red-bg)' : 'rgba(15,23,42,0.05)', color: hit === false ? 'var(--red)' : 'var(--text-md)' }}>{tname}</span>;
                              })}
                            </div>
                          </td>
                          <td className="text-center">{x ? (x.trajectory_recall >= 1 ? <Tick /> : <Cross>{pct(x.trajectory_recall, 0)}</Cross>) : '·'}</td>
                          <td className="text-center">{x ? (x.grounded ? <Tick /> : <Cross />) : '·'}</td>
                          <td className="text-center">{x ? (x.action_ok ? <Tick /> : <Cross />) : '·'}</td>
                          <td className="text-center">{x ? (x.faithful ? <Tick>{`✓ ${x.facts_hit}/${x.facts_checked}`}</Tick> : <Cross>{`${x.facts_hit}/${x.facts_checked}`}</Cross>) : '·'}</td>
                          <td className="text-right">{x ? `${x.latency_ms} ms` : '·'}</td>
                          <td className="text-right">{x?.cost_usd != null ? `$${x.cost_usd.toFixed(4)}` : '·'}</td>
                        </tr>
                        {isOpen && (
                          <tr>
                            <td colSpan={8} className="pb-2">
                              <div className="rounded-lg p-2.5 text-[10px]" style={{ background: 'rgba(255,255,255,0.6)', border: '1px solid var(--hairline)' }}>
                                <div className="grid grid-cols-3 gap-3">
                                  <div>
                                    <p className="font-bold uppercase tracking-widest text-[8.5px] mb-1" style={{ color: 'var(--text-faint)' }}>Agents on the path</p>
                                    <div className="flex flex-wrap gap-1">{(x?.observed_agents || c.expected_agents || []).map((a) => <AgentChip key={a} agent={a} />)}</div>
                                    {x?.missing_tools?.length > 0 && <p className="mt-1" style={{ color: 'var(--red)' }}>Missing: {x.missing_tools.join(', ')}</p>}
                                  </div>
                                  <div>
                                    <p className="font-bold uppercase tracking-widest text-[8.5px] mb-1" style={{ color: 'var(--text-faint)' }}>Checks</p>
                                    <p>Citations required: <b>{c.requires_citation ? 'yes' : 'no'}</b> · observed {x?.citations ?? '·'}</p>
                                    <p>Actions allowed: <b>{c.requires_action ? 'drafts → queue' : 'none'}</b> · drafted {x?.actions ?? '·'}</p>
                                    <p>Fact checks: <b>{(c.fact_checks || []).join(', ') || 'none'}</b></p>
                                    <p>Model: <b>{x?.model ?? '·'}</b>{x?.tokens ? ` · ${x.tokens.toLocaleString()} tokens · ${x.llm_calls} LLM calls` : ''}</p>
                                  </div>
                                  <div>
                                    <p className="font-bold uppercase tracking-widest text-[8.5px] mb-1" style={{ color: 'var(--text-faint)' }}>Answer preview</p>
                                    <p className="whitespace-pre-wrap" style={{ color: 'var(--text-dim)' }}>{x?.answer_preview ?? 'not run yet'}</p>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {r && (
              <p className="text-[9.5px] px-2 pt-1.5" style={{ color: 'var(--text-dim)' }}>
                Last run {new Date(r.run_at).toLocaleString()} · mode <b>{r.mode}</b>
                {live ? ` · total $${r.total_cost_usd?.toFixed(4)} for ${rows.length} questions` : ' · the direct tool run executes the same tools without the language model, so trajectory and faithfulness are real but tokens and cost are not measured'}
              </p>
            )}
          </Panel>
        </div>

        <div className="col-span-4 flex flex-col gap-2.5">
          <Panel title="What is measured, and what it maps to on Google Cloud">
            <div className="px-1 text-[10px] flex flex-col gap-1.5" style={{ color: 'var(--text-md)' }}>
              {[
                ['Tool-trajectory recall', 'Did the graph call every tool a clinician-reviewer said it must? Same idea as ADK\'s tool_trajectory_avg_score, scored in-order-agnostic.'],
                ['Groundedness', 'Clinical claims must carry a guideline citation (doc + page). On Google Cloud: the Gen AI Evaluation Service groundedness autorater on the citation spans.'],
                ['Action safety', 'A draft prescription / recall / referral may only appear as a queued item, never as a completed write. Zero tolerance.'],
                ['Numeric faithfulness', 'Every headline number in the answer is re-computed from the HIE tables and matched within tolerance. Catches the classic LLM failure: a fluent, wrong number.'],
                ['Latency · tokens · cost', 'Wall-clock per question, tokens from ADK usage metadata, priced at the list rates on the LLM tab.'],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="font-extrabold" style={{ color: 'var(--text)' }}>{k}</p>
                  <p style={{ color: 'var(--text-dim)' }}>{v}</p>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Release gate on Google Cloud">
            <div className="px-1 text-[10px]" style={{ color: 'var(--text-md)' }}>
              <p>The evalset file is ADK-compatible (<code className="text-[9px]">adk eval</code>). In Cloud Build it runs on every PR:</p>
              <ul className="mt-1 ml-3 list-disc" style={{ color: 'var(--text-dim)' }}>
                <li>trajectory recall ≥ 0.9, action safety = 1.0, faithfulness ≥ 0.95 → merge allowed</li>
                <li>LLM-judge rubric (Gemini 3.1 Pro) on tone, completeness and Arabic fidelity → advisory</li>
                <li>Cost per question tracked as an SLO; regression &gt; 20% blocks release</li>
                <li>Production sampling: 2% of live conversations replayed through the same scorer weekly</li>
              </ul>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────────── 3. LLM selection & cost ───────────────────────────── */
function LlmView() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { getLlmSelection().then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="p-6 text-[12px]" style={{ color: 'var(--red)' }}>LLM selection unavailable: {err}</div>;
  if (!d) return <Spinner />;
  const ac = d.architecture_comparison;
  const perAgent = Object.entries(ac.per_agent_schema_tokens).map(([k, v]) => ({ label: k.replace('_agent', '').replace('nabd_', ''), value: v }));
  const saving = ac.monthly_cost_flat_usd - ac.monthly_cost_hierarchical_usd;

  return (
    <div className="flex flex-col gap-2.5">
      <KpiStrip items={[
        { icon: 'coins', tone: 'maroon', label: `Production LLM cost / month on Google Cloud · supervisor + specialists (${ac.questions_per_day.toLocaleString()} q/day)`, value: `$${ac.monthly_cost_hierarchical_usd.toLocaleString()}` },
        { icon: 'coins', tone: 'gold', label: 'Same traffic · one flat agent carrying every tool', value: `$${ac.monthly_cost_flat_usd.toLocaleString()}`, trend: `+$${saving.toLocaleString()}/mo`, trendDir: 'down' },
        { icon: 'coins', tone: 'violet', label: 'Same traffic · Gemini 3.1 Pro everywhere', value: `$${ac.monthly_cost_hierarchical_pro_usd.toLocaleString()}`, trend: `${(ac.monthly_cost_hierarchical_pro_usd / ac.monthly_cost_hierarchical_usd).toFixed(1)}×`, trendDir: 'down' },
        { icon: 'activity', tone: 'sand', label: 'Budget after intro pricing ends (Jan 2027)', value: `$${ac.monthly_cost_hierarchical_usd_2027.toLocaleString()}` },
        { icon: 'gauge', tone: 'green', label: 'Prompt tokens read per hop: specialist vs flat', value: `${ac.hierarchical_supervisor_schema_tokens} / ${ac.flat_single_agent_schema_tokens}` },
      ]} />
      <p className="text-[10px] px-1 -mt-1" style={{ color: 'var(--text-dim)' }}>
        Model plan and cost projection for the Google Cloud deployment, at list prices. The demonstration runs the same agent graph, tools and evalset; the projection is what the production traffic would cost on the chosen models.
      </p>

      <div className="grid grid-cols-12 gap-2.5">
        <div className="col-span-7">
          <Panel title="Production model plan on Google Cloud: list prices per 1M tokens (Vertex AI / Gemini API price pages)"
            right={<span className="text-[9.5px]" style={{ color: 'var(--text-faint)' }}>as of {d.prices_as_of}</span>}>
            <div className="px-1">
              <table className="w-full text-[10px]">
                <thead>
                  <tr style={{ color: 'var(--text-faint)' }} className="text-left uppercase tracking-wider">
                    <th className="py-1 font-bold" style={{ width: 118 }}>Model</th><th className="font-bold">Role in Nabd</th>
                    <th className="font-bold text-right" style={{ width: 52 }}>In</th><th className="font-bold text-right" style={{ width: 58 }}>Out</th>
                    <th className="font-bold pl-3" style={{ width: 70 }}>Context</th><th className="font-bold" style={{ width: 58 }}>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {d.models.map((m) => (
                    <tr key={m.model} className="border-t border-[rgba(15,23,42,0.05)] align-top" style={{ color: 'var(--text-md)' }}>
                      <td className="py-1.5 pr-2">
                        <p className="font-mono font-bold text-[9.5px]" style={{ color: m.chosen ? 'var(--brand)' : 'var(--text)' }}>{m.model}</p>
                        <span className={`badge ${m.chosen ? 'badge-green' : m.role.startsWith('Avoid') ? 'badge-red' : 'badge-amber'}`} style={{ fontSize: 8 }}>
                          {m.chosen ? 'chosen' : m.role.startsWith('Avoid') ? 'avoided' : 'not used'}
                        </span>
                      </td>
                      <td className="pr-2">
                        <p className="font-semibold" style={{ color: 'var(--text)' }}>{m.role}</p>
                        <p style={{ color: 'var(--text-dim)' }}>{m.why}</p>
                        <p className="text-[9px] italic" style={{ color: 'var(--text-faint)' }}>{m.note}</p>
                      </td>
                      <td className="text-right font-bold">${m.in.toFixed(2)}</td>
                      <td className="text-right font-bold">{m.out ? `$${m.out.toFixed(2)}` : 'n/a'}</td>
                      <td className="pl-3">{m.context}</td><td>{m.latency}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>

        <div className="col-span-5 flex flex-col gap-2.5">
          <div style={{ height: 250 }}>
            <Panel title="Tool-schema tokens each agent must read on every hop">
              <Bar3D data={perAgent} ramp={0} maxBars={6} unit=" tok" />
            </Panel>
          </div>
          <Panel title="Why a supervisor with specialists rather than one agent: the token arithmetic">
            <div className="px-1 text-[10px]" style={{ color: 'var(--text-md)' }}>
              <p>A flat agent re-reads <b>{ac.flat_single_agent_schema_tokens.toLocaleString()}</b> schema tokens on each of ~{ac.typical_hops} tool rounds
                (≈ {ac.flat_tokens_per_turn_est.toLocaleString()} / turn). The supervisor reads <b>{ac.hierarchical_supervisor_schema_tokens}</b> and hands off to specialists
                that read only their own (≈ {ac.hierarchical_tokens_per_turn_est.toLocaleString()} / turn).</p>
              <p className="mt-1.5" style={{ color: 'var(--text-dim)' }}>{ac.argument}</p>
              <p className="mt-1.5 text-[9px] italic" style={{ color: 'var(--text-faint)' }}>{ac.assumptions} Output tokens are the same in both designs, so the gap is entirely the prompt.</p>
            </div>
          </Panel>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2.5">
        {[
          ['How the LLM was chosen', [
            'Function-calling reliability on our own evalset (trajectory recall): the metric that matters for an agent, not MMLU.',
            'Price per question at 3 hops: Flash 3.8 ≈ 0.6¢, Flash 3.5 ≈ 1.3¢, Pro 3.1 ≈ 1.9¢, and quality on structured tool tasks was indistinguishable.',
            'Lifecycle: 2.5 Flash retires Oct 2026; 3.1 Pro is still preview. Default must be GA and at least a year from deprecation.',
            'Latency: clinicians tolerate ~5 s for a briefing; Flash keeps p95 there with 3 hops, Pro does not.',
            'Region & residency: the model is called with pseudonymised, aggregated payloads only, so the endpoint region is a latency question, not a PHI question.',
          ]],
          ['Where Pro is used deliberately', [
            'LLM-as-judge in evaluation: grading needs depth; it runs offline and on 10 cases, so cost is irrelevant.',
            'Long executive syntheses on request (monthly ministry report), one call per report, not per question.',
            'Nothing on the hot path. If a Flash answer fails a faithfulness check in production it is flagged, not silently escalated to Pro.',
          ]],
          ['What would change the decision', [
            'Trajectory recall on Flash dropping below 0.9 after a model update → pin the version and re-evaluate.',
            'Arabic clinical fidelity scores (LLM-judge) trailing Pro by > 10 points → route Arabic voice turns to Pro.',
            'Traffic > 100k q/day → move to Provisioned Throughput; unit price falls and latency becomes predictable.',
            'MedGemma becoming GA on Agent Platform → evaluate for note summarisation only, never for risk scoring.',
          ]],
        ].map(([title, items]) => (
          <Panel key={title} title={title}>
            <ul className="px-2 ml-3 list-disc text-[10px] flex flex-col gap-1" style={{ color: 'var(--text-md)' }}>
              {items.map((x) => <li key={x}>{x}</li>)}
            </ul>
          </Panel>
        ))}
      </div>
    </div>
  );
}

/* ───────────────────────────── 4. Governance ───────────────────────────── */
function GovernanceView() {
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => { getGovernance().then(setD).catch((e) => setErr(e.message)); }, []);
  if (err) return <div className="p-6 text-[12px]" style={{ color: 'var(--red)' }}>Governance unavailable: {err}</div>;
  if (!d) return <Spinner />;
  const impl = d.filter((x) => x.status === 'implemented').length;
  const areas = [...new Set(d.map((x) => x.area))];
  return (
    <div className="flex flex-col gap-2.5">
      <KpiStrip items={[
        { icon: 'check', tone: 'green', label: 'Controls implemented in this demonstration', value: impl, suffix: `/ ${d.length}` },
        { icon: 'activity', tone: 'gold', label: 'Controls delivered by Google Cloud services', value: d.length - impl },
        { icon: 'alert', tone: 'maroon', label: 'Autonomous clinical writes permitted', value: 0 },
        { icon: 'users', tone: 'sand', label: 'Real patient records touched', value: 0 },
      ]} />
      <div className="grid grid-cols-2 gap-2.5">
        {areas.map((a) => (
          <Panel key={a} title={a}>
            <div className="px-1 flex flex-col gap-1.5">
              {d.filter((x) => x.area === a).map((x) => (
                <div key={x.control} className="flex items-start gap-2 text-[10px] rounded-lg px-2 py-1.5"
                  style={{ background: 'rgba(255,255,255,0.55)', border: '1px solid var(--hairline)' }}>
                  <span className={`badge ${x.status === 'implemented' ? 'badge-green' : 'badge-amber'} shrink-0`} style={{ fontSize: 8, marginTop: 1 }}>
                    {x.status === 'implemented' ? 'implemented' : 'Google Cloud'}
                  </span>
                  <div className="min-w-0">
                    <p className="font-semibold" style={{ color: 'var(--text)' }}>{x.control}</p>
                    <p style={{ color: 'var(--text-faint)' }}>Evidence: {x.evidence}</p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        ))}
      </div>
      <div className="glass-card px-4 py-2.5 text-[10.5px]" style={{ color: 'var(--text-md)' }}>
        <b style={{ color: 'var(--text)' }}>Regulatory frame.</b> Qatar PDPPL (Law 13/2016) treats health data as sensitive personal data, processing needs a lawful basis and a
        permit; the National Health Strategy requires auditability of decision support. The design answer is the same in every lane: PHI stays in Doha, the
        model never prescribes, every automated inference is logged with its inputs, and a human owns every clinical write.
      </div>
    </div>
  );
}

/* ───────────────────────────── page ───────────────────────────── */
export default function EvaluationPage() {
  const [view, setView] = useState('model');
  const sub = useMemo(() => ({
    model: 'The deterioration-risk model, evaluated on 1,000 held-out patients: discrimination, calibration, threshold trade-offs and subgroup fairness.',
    agents: 'Ten representative clinician and ministry questions, run through the live agent graph and scored against ground truth.',
    llm: 'Model selection rationale, cost per question, and the measured case for a supervisor with specialists over a single agent.',
    governance: 'The control list: implemented in this demonstration, delivered by Google Cloud services in the target architecture, and never permitted.',
  })[view], [view]);

  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="flex items-end justify-between px-1 mb-2.5">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Evaluation: model and agent performance
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>{sub}</p>
        </div>
        <div className="seg-track">
          {VIEWS.map(([k, l]) => (
            <button key={k} className={`seg-pill ${view === k ? 'active' : ''}`} onClick={() => setView(k)}>{l}</button>
          ))}
        </div>
      </div>
      {view === 'model' && <ModelView />}
      {view === 'agents' && <AgentsView />}
      {view === 'llm' && <LlmView />}
      {view === 'governance' && <GovernanceView />}
    </div>
  );
}
