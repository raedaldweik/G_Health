import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ReferenceLine, LabelList,
} from 'recharts';
import { useApp } from '../context/AppContext';
import {
  getSimPatients, getSimBaseline, getSimPreset, postSimulate, streamExplain,
} from '../services/api';
import { Panel, Spinner } from '../components/ui';

/*
 * What-if simulator — one patient, the deployed deterioration-risk model, live.
 *   Left    · the levers a clinician can move (record values marked, changes in gold)
 *   Centre  · baseline vs simulated risk: gauge, band, registry percentile, cost, gaps closed
 *   Right   · which features moved the estimate (model attribution) and Gemini's explanation
 * Every number comes from the backend: the model is re-scored on each change (debounced).
 */

const BAND_COLOR = { Low: '#3a8e5a', Moderate: '#b8862e', High: '#d97706', 'Very High': '#9b1c46' };
const UP = '#b03c3c';
const DOWN = '#3a8e5a';

const pct = (p, d = 1) => (p == null ? '—' : `${(p * 100).toFixed(d)}%`);
const qar = (n) => (n == null ? '—' : `${n < 0 ? '−' : n > 0 ? '+' : ''}QAR ${Math.abs(n).toLocaleString()}`);

function fmtLever(l, v) {
  if (v == null) return '—';
  if (l.kind === 'toggle') return v ? 'Yes' : 'No';
  if (l.percent) return `${Math.round(v * 100)}%`;
  if (Number.isInteger(+l.step) && +l.step >= 1) return `${Math.round(v)}${l.unit ? ` ${l.unit}` : ''}`;
  return `${(+v).toFixed(1)}${l.unit ? ` ${l.unit}` : ''}`;
}

const md = {
  p: (p) => <p {...p} />,
  strong: (p) => <strong style={{ color: 'var(--brand)', fontWeight: 700 }} {...p} />,
};

/* ── Gauge: semicircle, baseline arc faint, simulated arc coloured by band ── */
function arc(cx, cy, r, a0, a1) {
  const p = (a) => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const [x0, y0] = p(a0); const [x1, y1] = p(a1);
  const large = a1 - a0 > Math.PI ? 1 : 0;
  return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`;
}
function Gauge({ base, sim, changed }) {
  const W = 260, H = 150, cx = 130, cy = 132, R = 106;
  const ang = (p) => Math.PI + Math.PI * Math.min(Math.max(p, 0), 1);
  const bandStops = [[0, 0.05, BAND_COLOR.Low], [0.05, 0.12, BAND_COLOR.Moderate], [0.12, 0.25, BAND_COLOR.High], [0.25, 1, BAND_COLOR['Very High']]];
  const cur = sim ?? base;
  const color = BAND_COLOR[cur?.band] || 'var(--brand)';
  return (
    <div className="relative flex flex-col items-center">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="overflow-visible">
        {bandStops.map(([a, b, c]) => (
          <path key={a} d={arc(cx, cy, R + 12, ang(a) + 0.004, ang(b) - 0.004)} stroke={c} strokeOpacity="0.22" strokeWidth="3" fill="none" />
        ))}
        <path d={arc(cx, cy, R, Math.PI, 2 * Math.PI)} stroke="rgba(15,23,42,0.08)" strokeWidth="14" fill="none" strokeLinecap="round" />
        {base && (
          <path d={arc(cx, cy, R, Math.PI, Math.max(ang(base.probability), Math.PI + 0.02))}
            stroke="rgba(15,23,42,0.22)" strokeWidth="14" fill="none" strokeLinecap="round" />
        )}
        {cur && (
          <path d={arc(cx, cy, R, Math.PI, Math.max(ang(cur.probability), Math.PI + 0.02))}
            stroke={color} strokeWidth={changed ? 14 : 14} fill="none" strokeLinecap="round"
            style={{ transition: 'all 0.45s cubic-bezier(.2,.8,.2,1)', filter: `drop-shadow(0 2px 6px ${color}55)` }} />
        )}
        {base && changed && (() => {
          const a = ang(base.probability); const x = cx + R * Math.cos(a); const y = cy + R * Math.sin(a);
          return <circle cx={x} cy={y} r="4.5" fill="#fff" stroke="rgba(15,23,42,0.5)" strokeWidth="1.5" />;
        })()}
        <text x={cx - R - 2} y={cy + 16} fontSize="9" fill="var(--text-faint)" textAnchor="middle" fontWeight="700">0%</text>
        <text x={cx + R + 2} y={cy + 16} fontSize="9" fill="var(--text-faint)" textAnchor="middle" fontWeight="700">100%</text>
      </svg>
      <div className="absolute left-0 right-0 flex flex-col items-center" style={{ top: 66 }}>
        <div className="text-[9px] font-bold uppercase tracking-[0.14em]" style={{ color: 'var(--text-faint)' }}>
          {changed ? 'Simulated · 12 mo' : 'Model risk · 12 mo'}
        </div>
        <div className="font-extrabold tracking-tight leading-none" style={{ fontSize: 40, color, fontFeatureSettings: '"tnum" 1', transition: 'color 0.3s' }}>
          {pct(cur?.probability)}
        </div>
        <div className="text-[11px] font-bold mt-1 flex items-center gap-1.5" style={{ color: 'var(--text-dim)' }}>
          {changed ? (<><span style={{ textDecoration: 'line-through', opacity: 0.7 }}>{pct(base?.probability)}</span>
            <span className="badge" style={{ background: `${color}18`, color, border: `1px solid ${color}44` }}>{cur?.band}</span></>)
            : <span className="badge" style={{ background: `${color}18`, color, border: `1px solid ${color}44` }}>{cur?.band}</span>}
        </div>
      </div>
    </div>
  );
}

/* ── One lever row ── */
function Lever({ l, value, recordValue, onChange }) {
  const changed = recordValue != null ? (l.kind === 'toggle' ? !!value !== !!recordValue : Math.abs(+value - +recordValue) > 1e-9)
    : value != null;
  const dirTxt = l.direction > 0 ? 'higher → more risk' : l.direction < 0 ? 'higher → less risk' : 'unconstrained';
  if (l.kind === 'toggle') {
    return (
      <div className="flex items-center justify-between gap-3 py-1.5 border-b border-[rgba(15,23,42,0.05)] last:border-0">
        <div className="min-w-0">
          <div className="text-[11.5px] font-bold leading-tight" style={{ color: changed ? 'var(--gold)' : 'var(--text)' }}>{l.label}</div>
          <div className="text-[9.5px] leading-snug truncate" style={{ color: 'var(--text-faint)' }}>
            {l.hint || dirTxt}{changed ? ` · record: ${fmtLever(l, recordValue)}` : ''}
          </div>
        </div>
        <button type="button" aria-label={l.label} className={`lever-toggle ${value ? 'on' : ''} ${changed ? 'changed' : ''}`}
          onClick={() => onChange(value ? 0 : 1)} />
      </div>
    );
  }
  const v = value == null ? (l.min + l.max) / 2 : +value;
  const pctPos = ((v - l.min) / (l.max - l.min)) * 100;
  return (
    <div className="py-1.5 border-b border-[rgba(15,23,42,0.05)] last:border-0">
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-[11.5px] font-bold leading-tight" style={{ color: changed ? 'var(--gold)' : 'var(--text)' }}>{l.label}</div>
        <div className="text-[12px] font-extrabold tabular-nums flex items-baseline gap-1.5" style={{ color: changed ? 'var(--gold)' : 'var(--text)' }}>
          {changed && <span className="text-[9.5px] font-bold" style={{ color: 'var(--text-faint)', textDecoration: 'line-through' }}>{fmtLever(l, recordValue)}</span>}
          {fmtLever(l, value == null ? v : value)}
        </div>
      </div>
      <input type="range" className={`lever-range ${changed ? 'changed' : ''}`} min={l.min} max={l.max} step={l.step}
        value={v} style={{ '--pct': `${pctPos}%` }} aria-label={l.label}
        onChange={(e) => onChange(+e.target.value)} />
      <div className="flex justify-between text-[9.5px] leading-snug" style={{ color: 'var(--text-faint)' }}>
        <span className="truncate pr-2">{l.hint || ''}</span>
        <span className="shrink-0">{dirTxt}</span>
      </div>
    </div>
  );
}

export default function SimulatorPage() {
  const { persona } = useApp() || {};
  const [pick, setPick] = useState(null);            // {presets, matches}
  const [q, setQ] = useState('');
  const [open, setOpen] = useState(false);
  const [pid, setPid] = useState(null);
  const [base, setBase] = useState(null);
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [explain, setExplain] = useState({ text: '', mode: null, model: null, running: false, stale: false, error: null });
  const abortRef = useRef(null);
  const explainAbort = useRef(null);

  // patient list + default (the demo's hero)
  useEffect(() => {
    getSimPatients('').then((p) => { setPick(p); if (!pid && p.presets?.length) setPid(p.presets[0].patient_id); })
      .catch((e) => setErr(e.message));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!q.trim()) return undefined;
    const t = setTimeout(() => getSimPatients(q).then((p) => setPick((old) => ({ ...(old || {}), ...p }))).catch(() => {}), 220);
    return () => clearTimeout(t);
  }, [q]);

  // baseline on patient change
  useEffect(() => {
    if (!pid) return;
    setBase(null); setResult(null); setErr(null);
    setExplain({ text: '', mode: null, model: null, running: false, stale: false, error: null });
    getSimBaseline(pid).then((b) => { setBase(b); setValues(b.values || {}); }).catch((e) => setErr(e.message));
  }, [pid]);

  const levers = base?.levers || [];
  const overrides = useMemo(() => {
    if (!base) return {};
    const o = {};
    for (const l of levers) {
      const rv = base.values[l.key]; const v = values[l.key];
      if (v == null) continue;
      if (rv == null || (l.kind === 'toggle' ? !!v !== !!rv : Math.abs(+v - +rv) > 1e-9)) o[l.key] = v;
    }
    return o;
  }, [base, values, levers]);
  const changed = Object.keys(overrides).length > 0;

  // debounced re-score
  useEffect(() => {
    if (!base || base.consent === 'DENIED') return undefined;
    abortRef.current?.abort();
    const ctrl = new AbortController(); abortRef.current = ctrl;
    setBusy(true);
    const t = setTimeout(() => {
      postSimulate(pid, overrides, ctrl.signal)
        .then((r) => { if (!ctrl.signal.aborted) { setResult(r); setBusy(false); } })
        .catch((e) => { if (e.name !== 'AbortError') { setErr(e.message); setBusy(false); } });
    }, 180);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [base, pid, overrides]);

  // an explanation goes stale as soon as a lever moves
  useEffect(() => { setExplain((x) => (x.text && !x.running ? { ...x, stale: true } : x)); }, [overrides]);

  const setLever = useCallback((k, v) => setValues((old) => ({ ...old, [k]: v })), []);
  const reset = () => { if (base) setValues(base.values); };
  const applyPreset = (id) => getSimPreset(pid, id).then(({ overrides: o }) => setValues({ ...(base?.values || {}), ...o })).catch(() => {});

  const runExplain = () => {
    explainAbort.current?.abort();
    const ctrl = new AbortController(); explainAbort.current = ctrl;
    setExplain({ text: '', mode: null, model: null, running: true, stale: false, error: null });
    streamExplain({ patientId: pid, overrides, actor: persona || 'clinician' }, (ev) => {
      if (ev.type === 'meta') setExplain((x) => ({ ...x, mode: ev.mode, model: ev.model }));
      else if (ev.type === 'token') setExplain((x) => ({ ...x, text: x.text + ev.text }));
      else if (ev.type === 'final') setExplain((x) => ({ ...x, text: ev.text || x.text, mode: ev.mode, model: ev.model || x.model, running: false, error: ev.error || null }));
    }, ctrl.signal).catch((e) => { if (e.name !== 'AbortError') setExplain((x) => ({ ...x, running: false, error: e.message })); });
  };

  const groups = useMemo(() => {
    const g = new Map();
    for (const l of levers) { if (!g.has(l.group)) g.set(l.group, []); g.get(l.group).push(l); }
    return [...g.entries()];
  }, [levers]);

  const attribution = useMemo(() => (result?.attribution || []).slice(0, 8).map((a) => ({
    ...a, pts: +(a.delta_probability * 100).toFixed(1),
    change: a.from !== a.to && a.from != null ? `${fmtAttr(a.feature, a.from)} → ${fmtAttr(a.feature, a.to)}` : 'via interactions',
  })), [result]);
  const changeOf = useMemo(() => Object.fromEntries(attribution.map((a) => [a.label, a.change])), [attribution]);
  const AttrTick = ({ x, y, payload }) => (
    <text x={x} y={y} textAnchor="end">
      <tspan x={x} dy="-1" fontSize="10.5" fontWeight="700" fill="#1e293b">{payload.value}</tspan>
      <tspan x={x} dy="11" fontSize="9" fontWeight="600" fill="#94a3b8">{changeOf[payload.value]}</tspan>
    </text>
  );

  const pt = base?.patient;
  const sim = result?.simulated; const b0 = result?.baseline || base?.risk;

  return (
    <div className="h-full p-3 overflow-hidden flex flex-col gap-2.5">
      {/* ── header ── */}
      <div className="flex items-end justify-between gap-4 shrink-0 px-1">
        <div className="min-w-0">
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Risk Simulator — what changes one patient's deterioration risk
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
            Move a lever and the deployed model re-scores the patient. The attribution shows which inputs moved the estimate; Gemini explains it in clinical language. Decision support, not a treatment recommendation.
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {(pick?.presets || []).map((p) => (
            <button key={p.patient_id} className={`sim-chip ${p.patient_id === pid ? 'active' : ''}`} onClick={() => setPid(p.patient_id)} title={p.tag}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: BAND_COLOR[bandOf(p.probability)] }} />
              <span>{p.name}</span>
              <span className="font-normal" style={{ color: 'var(--text-faint)' }}>{pct(p.probability, 0)}</span>
            </button>
          ))}
          <div className="relative">
            <input value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
              onBlur={() => setTimeout(() => setOpen(false), 150)} placeholder="Search patient ID or name"
              className="text-[11px] px-3 py-[6px] rounded-full outline-none w-[190px]"
              style={{ background: 'rgba(255,255,255,0.75)', border: '1px solid rgba(15,23,42,0.1)', color: 'var(--text)' }} />
            {open && q.trim() && (pick?.matches || []).length > 0 && (
              <div className="absolute right-0 mt-1 z-50 glass-card p-1 w-[300px]" style={{ background: 'rgba(255,255,255,0.97)' }}>
                {pick.matches.map((m) => (
                  <button key={m.patient_id} className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-[rgba(138,21,56,0.06)] flex items-center justify-between gap-2"
                    onMouseDown={() => { setPid(m.patient_id); setQ(''); setOpen(false); }}>
                    <span className="text-[11px] font-bold truncate" style={{ color: 'var(--text)' }}>{m.name} <span className="font-mono font-normal" style={{ color: 'var(--text-faint)' }}>{m.patient_id}</span></span>
                    <span className="text-[10px] shrink-0" style={{ color: 'var(--text-dim)' }}>{m.age} · {m.diabetes_type === 'type1' ? 'T1' : 'T2'} · HbA1c {m.hba1c_latest ?? '—'} · {m.registry_tier}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {err && <div className="text-[12px] px-1" style={{ color: 'var(--red)' }}>Simulator unavailable: {err}</div>}
      {!base && !err && <Spinner />}

      {base?.consent === 'DENIED' && (
        <div className="glass-card p-5 text-[12.5px]" style={{ color: 'var(--red)' }}>{base.message}</div>
      )}

      {base && pt && (
        <div className="flex-1 grid grid-cols-12 gap-2.5 min-h-0">
          {/* ── levers ── */}
          <div className="col-span-4 min-h-0">
            <Panel title="Levers — the record, and what you change" pad={false}
              right={
                <div className="flex items-center gap-1">
                  <button className="sim-chip" onClick={reset} disabled={!changed}>Reset</button>
                  {(base.presets || []).map((p) => (
                    <button key={p.id} className="sim-chip" title={p.description} onClick={() => applyPreset(p.id)}>{p.label}</button>
                  ))}
                </div>
              }>
              <div className="h-full min-h-0 overflow-y-auto px-3.5 pb-3">
                <div className="flex items-center gap-2 py-2 border-b border-[rgba(15,23,42,0.06)]">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center text-[12px] font-extrabold shrink-0"
                    style={{ background: 'var(--brand-grad)', color: '#fff' }}>{initials(pt.name)}</div>
                  <div className="min-w-0 flex-1">
                    <div className="text-[12.5px] font-extrabold leading-tight truncate" style={{ color: 'var(--text)' }}>
                      {pt.name} <span className="font-mono text-[10px] font-normal" style={{ color: 'var(--text-faint)' }}>{pt.patient_id}</span>
                    </div>
                    <div className="text-[10px] leading-snug truncate" style={{ color: 'var(--text-dim)' }}>
                      {pt.age} · {pt.gender} · {pt.nationality} · {pt.diabetes_type === 'type1' ? 'Type 1' : 'Type 2'} for {Math.round(pt.years_since_diagnosis)} y · {pt.facility}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-[9px] font-bold uppercase tracking-wider" style={{ color: 'var(--text-faint)' }}>Registry tier</div>
                    <div className="text-[11px] font-extrabold" style={{ color: BAND_COLOR[pt.registry_tier] || 'var(--text)' }}>{pt.registry_tier}</div>
                  </div>
                </div>
                {pt.open_care_gaps?.length > 0 && (
                  <div className="text-[9.5px] leading-snug py-1.5 border-b border-[rgba(15,23,42,0.06)]" style={{ color: 'var(--text-dim)' }}>
                    <b style={{ color: 'var(--text-md)' }}>{pt.open_care_gaps.length} open care gaps:</b> {pt.gap_labels.join(' · ')}
                  </div>
                )}
                {groups.map(([g, ls]) => (
                  <div key={g}>
                    <div className="sim-group-title">{g}</div>
                    {ls.map((l) => (
                      <Lever key={l.key} l={l} value={values[l.key]} recordValue={base.values[l.key]} onChange={(v) => setLever(l.key, v)} />
                    ))}
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          {/* ── risk ── */}
          <div className="col-span-3 min-h-0">
            <Panel title="Model estimate — before and after" right={busy && <span className="text-[9.5px] font-bold" style={{ color: 'var(--text-faint)' }}>re-scoring…</span>}>
              <div className="h-full min-h-0 flex flex-col overflow-y-auto">
                <Gauge base={b0} sim={sim} changed={changed} />
                <div className="grid grid-cols-2 gap-1.5 mt-1">
                  <Stat label="Change" value={changed && result ? `${result.delta.absolute >= 0 ? '+' : '−'}${Math.abs(result.delta.absolute * 100).toFixed(1)} pts` : '—'}
                    sub={changed && result ? `${result.delta.relative_pct >= 0 ? '+' : '−'}${Math.abs(result.delta.relative_pct).toFixed(0)}% relative` : 'move a lever'}
                    tone={changed && result ? (result.delta.absolute < 0 ? 'good' : 'bad') : null} />
                  <Stat label="Registry percentile" value={sim ? `${sim.percentile.toFixed(0)}th` : b0 ? `${b0.percentile.toFixed(0)}th` : '—'}
                    sub={changed && b0 ? `was ${b0.percentile.toFixed(0)}th · higher risk than that share of the registry` : 'higher risk than this share of the registry'} />
                  <Stat label="Expected cost · 12 months" value={changed && result ? qar(result.expected_cost_delta_qar) : '—'}
                    sub={`at QAR ${(base.event_cost_qar || 18500).toLocaleString()} per deterioration episode`}
                    tone={changed && result ? (result.expected_cost_delta_qar < 0 ? 'good' : 'bad') : null} />
                  <Stat label="Band" value={sim ? sim.band : b0?.band || '—'}
                    sub={changed && b0 && sim && b0.band !== sim.band ? `was ${b0.band}` : 'model band (registry tier ' + pt.registry_tier + ')'}
                    color={BAND_COLOR[sim?.band || b0?.band]} />
                </div>
                <div className="mt-2 text-[10px] leading-relaxed" style={{ color: 'var(--text-dim)' }}>
                  <div className="text-[9.5px] font-bold uppercase tracking-[0.14em] mb-1" style={{ color: 'var(--text-faint)' }}>Care gaps</div>
                  {result?.gaps?.closed?.length ? result.gaps.closed.map((g) => (
                    <div key={g} className="flex items-start gap-1.5"><span style={{ color: DOWN }}>✓</span><span>Closes: {g}</span></div>
                  )) : null}
                  {result?.gaps?.opened?.length ? result.gaps.opened.map((g) => (
                    <div key={g} className="flex items-start gap-1.5"><span style={{ color: UP }}>!</span><span>Opens: {g}</span></div>
                  )) : null}
                  <div style={{ color: 'var(--text-faint)' }}>
                    {result ? `${result.gaps.open_after} open after the change` : `${pt.open_care_gaps.length} open on the record`}
                    {changed && result && !result.gaps.closed.length && !result.gaps.opened.length ? ' · none closed or opened' : ''}
                  </div>
                </div>
              </div>
            </Panel>
          </div>

          {/* ── attribution + explanation ── */}
          <div className="col-span-5 min-h-0 grid grid-rows-2 gap-2.5">
            <Panel title="What moved the estimate — model attribution (probability points)">
              {changed && attribution.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={attribution} layout="vertical" margin={{ top: 4, right: 44, bottom: 0, left: 4 }} barCategoryGap={5}>
                    <XAxis type="number" tick={{ fontSize: 9.5, fill: '#94a3b8' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}`}
                      domain={[(min) => Math.min(Math.floor(min * 1.35), -1), (max) => Math.max(Math.ceil(max * 1.35), 1)]} />
                    <YAxis type="category" dataKey="label" width={150} tick={<AttrTick />} axisLine={false} tickLine={false} interval={0} />
                    <ReferenceLine x={0} stroke="rgba(15,23,42,0.25)" />
                    <Tooltip cursor={{ fill: 'rgba(15,23,42,0.03)' }} formatter={(v) => [`${v > 0 ? '+' : ''}${v} pts`, 'contribution to the change']}
                      contentStyle={{ fontSize: 11, borderRadius: 10, border: '1px solid rgba(15,23,42,0.08)' }} />
                    <Bar dataKey="pts" radius={[4, 4, 4, 4]} isAnimationActive animationDuration={350}>
                      {attribution.map((a) => <Cell key={a.feature} fill={a.pts > 0 ? UP : DOWN} fillOpacity={0.85} />)}
                      <LabelList dataKey="pts" position="right" style={{ fontSize: 10, fontWeight: 700, fill: '#475569' }} formatter={(v) => `${v > 0 ? '+' : ''}${v}`} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex flex-col justify-center gap-1.5 px-1">
                  <div className="text-[10px] font-bold uppercase tracking-[0.14em]" style={{ color: 'var(--text-faint)' }}>Baseline drivers on the record</div>
                  {(base.drivers || []).slice(0, 6).map((d) => (
                    <div key={d.feature} className="flex items-center gap-2 text-[11px]">
                      <span className="w-[150px] truncate font-semibold" style={{ color: 'var(--text-md)' }}>{d.label}</span>
                      <span className="w-[54px] tabular-nums" style={{ color: 'var(--text-dim)' }}>{fmtAttr(d.feature, d.value)}</span>
                      <div className="flex-1 h-[6px] rounded-full overflow-hidden" style={{ background: 'rgba(15,23,42,0.06)' }}>
                        <div className="h-full rounded-full" style={{ width: `${Math.min(100, Math.abs(d.contribution) / Math.abs(base.drivers[0].contribution) * 100)}%`, background: d.contribution > 0 ? UP : DOWN, opacity: 0.85 }} />
                      </div>
                      <span className="w-[44px] text-right tabular-nums text-[10px] font-bold" style={{ color: d.contribution > 0 ? UP : DOWN }}>{d.contribution > 0 ? '+' : ''}{d.contribution.toFixed(2)}</span>
                    </div>
                  ))}
                  <div className="text-[9.5px] mt-1" style={{ color: 'var(--text-faint)' }}>SHAP-style contributions in log-odds; move a lever to see what changes the estimate.</div>
                </div>
              )}
            </Panel>

            <Panel title="Why — explanation"
              right={
                <div className="flex items-center gap-1.5">
                  {explain.mode && (
                    <span className="badge badge-blue" title={explain.mode}>
                      {explain.mode === 'gemini' ? explain.model : explain.mode === 'scripted' ? 'templated · no LLM key' : `fallback · ${explain.model || ''}`}
                    </span>
                  )}
                  <button className={`sim-chip ${!explain.text || explain.stale ? 'active' : ''}`} onClick={runExplain} disabled={explain.running || !result}>
                    <GIcon /> {explain.running ? 'Explaining…' : explain.text ? 'Explain again' : 'Explain with Gemini'}
                  </button>
                </div>
              }>
              <div className="h-full min-h-0 flex flex-col">
                <div className="flex-1 min-h-0 overflow-y-auto text-[12px] leading-relaxed sim-explain pr-1" style={{ color: 'var(--text-md)' }}>
                  {explain.text ? (
                    <div style={{ opacity: explain.stale ? 0.55 : 1, transition: 'opacity 0.2s' }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>{explain.text}</ReactMarkdown>
                      {explain.running && <span className="sim-cursor" />}
                    </div>
                  ) : explain.running ? (
                    <div className="flex items-center gap-2 text-[11px]" style={{ color: 'var(--text-dim)' }}><span className="sim-cursor" /> Gemini is reading the model output…</div>
                  ) : (
                    <div className="text-[11px]" style={{ color: 'var(--text-dim)' }}>
                      {changed
                        ? 'Ask Gemini to explain why the estimate moved. It is given the before-and-after scores, the attribution and the gaps closed, and asked to narrate them for the treating clinician.'
                        : 'Move a lever, then ask Gemini to explain the change. The explanation is grounded in the model output shown on this page; Gemini adds no numbers of its own.'}
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between gap-2 pt-1.5 mt-1 border-t border-[rgba(15,23,42,0.06)] text-[9.5px]" style={{ color: 'var(--text-faint)' }}>
                  <span>{explain.stale ? 'Levers changed since this explanation.' : explain.error ? `Gemini unavailable (${explain.error}); templated explanation shown.` : `Deterioration-risk model v${base.model_version || '2.1.0'} · association, not a causal treatment effect · logged to the audit trail`}</span>
                </div>
              </div>
            </Panel>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, sub, tone, color }) {
  const c = color || (tone === 'good' ? DOWN : tone === 'bad' ? UP : 'var(--text)');
  return (
    <div className="rounded-xl px-2.5 py-2" style={{ background: 'rgba(255,255,255,0.55)', border: '1px solid rgba(15,23,42,0.06)' }}>
      <div className="text-[9px] font-bold uppercase tracking-[0.14em]" style={{ color: 'var(--text-faint)' }}>{label}</div>
      <div className="text-[16px] font-extrabold tabular-nums leading-tight mt-0.5" style={{ color: c }}>{value}</div>
      <div className="text-[9.5px] leading-snug" style={{ color: 'var(--text-faint)' }}>{sub}</div>
    </div>
  );
}

function GIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9.1 3.6l6.8-6.8C35.8 2.4 30.3 0 24 0 14.6 0 6.5 5.4 2.6 13.2l7.9 6.1C12.4 13.6 17.7 9.5 24 9.5z" />
      <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v9h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8c4.4-4.1 7.1-10.1 7.1-17.5z" />
      <path fill="#FBBC05" d="M10.5 28.7A14.5 14.5 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7l-7.9-6.1A24 24 0 0 0 0 24c0 3.9.9 7.5 2.6 10.8l7.9-6.1z" />
      <path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.5-5.8c-2.1 1.4-4.9 2.3-8.4 2.3-6.3 0-11.6-4.1-13.5-9.9l-7.9 6.1C6.5 42.6 14.6 48 24 48z" />
    </svg>
  );
}

function initials(n) { return (n || '?').split(' ').map((s) => s[0]).slice(0, 2).join('').toUpperCase(); }
function bandOf(p) { return p >= 0.25 ? 'Very High' : p >= 0.12 ? 'High' : p >= 0.05 ? 'Moderate' : 'Low'; }
function fmtAttr(feature, v) {
  if (v == null) return '—';
  if (['smoker', 'on_metformin', 'on_sglt2_glp1', 'on_insulin', 'on_raas_inhibitor', 'albuminuria', 'retinopathy', 'neuropathy', 'foot_ulcer_history', 'htn', 'is_male'].includes(feature)) return v ? 'yes' : 'no';
  if (feature === 'adherence_pdc') return `${Math.round(v * 100)}%`;
  return Number.isInteger(+v) ? `${v}` : (+v).toFixed(1);
}
