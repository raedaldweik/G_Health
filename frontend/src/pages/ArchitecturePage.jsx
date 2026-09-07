import { useMemo, useState } from 'react';
import {
  ADRS, AVOIDED_ADMISSION_USD, COST, DATA_FLOWS, EDGES, EDGE_STYLE, FLOWS, LANES, NODES, PHASES, SCALE,
} from '../data/architecture';
import { Bar3D } from '../components/Chart3D';
import { KpiStrip, Panel } from '../components/ui';

/*
 * Architecture — the target design on Google Cloud, drawn as a deployable system.
 *   Diagram  · six lanes, four edge kinds, click any node for why / scale / alternative / phase-1 / cost
 *   Flows    · what is real-time, what is batch, and why
 *   Scale    · capacity model and inference story
 *   ADRs     · ten decisions with consequences
 *   Phases   · what changes between Railway (today) and Google Cloud, and what does not
 *   Cost     · order-of-magnitude monthly run cost at Doha list prices
 */

const VIEWS = [
  ['diagram', 'Diagram'], ['flows', 'Real-time vs batch'], ['scale', 'Scale & inference'],
  ['adrs', 'Decisions (ADRs)'], ['phases', 'Phase 1 → 2'], ['cost', 'Run cost'],
];

/* ── geometry ── */
const PAD = 12, LW = 200, GAP = 24, H = 58, ROW = 72, TOP = 50;
const XC = 3, XH = 26, XG = 8;   // cross-cutting bars
const MAX_ROWS = Math.max(...NODES.map((n) => n.row)) + 1;
const BODY_BOTTOM = TOP + MAX_ROWS * ROW;
const RETURN_Y = BODY_BOTTOM + 10;
const XCUT_TOP = RETURN_Y + 22;
const W = PAD * 2 + LANES.length * LW + (LANES.length - 1) * GAP;
const HGT = XCUT_TOP + XC * (XH + XG) + 4;
const LANE_TINT = ['#8a6a4e', '#b8862e', '#8A1538', '#6d4fa8', '#a8407a', '#3a8e5a'];

const nx = (n) => PAD + n.lane * (LW + GAP);
const ny = (n) => TOP + n.row * ROW;
const BY_ID = Object.fromEntries(NODES.map((n) => [n.id, n]));

function edgePath(a, b) {
  const ax = nx(a), ay = ny(a), bx = nx(b), by = ny(b);
  if (b.lane > a.lane) {                                // forward: right-mid → left-mid
    const x1 = ax + LW, y1 = ay + H / 2, x2 = bx, y2 = by + H / 2;
    const mx = (x1 + x2) / 2;
    return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
  }
  if (b.lane === a.lane) {                              // same lane: loop out the right side
    const x = ax + LW, y1 = ay + H / 2, y2 = by + H / 2, o = x + 22;
    return `M${x},${y1} C${o},${y1} ${o},${y2} ${x},${y2}`;
  }
  // backward: drop from the bottom of the source, travel along the return rail, rise into the target
  const x1 = ax + LW / 2, y1 = ay + H, x2 = bx + LW / 2, y2 = by + H;
  return `M${x1},${y1} C${x1},${RETURN_Y} ${x2},${RETURN_Y} ${x2},${y2}`;
}

const XCUTS = [
  ['Security & sovereignty', 'Assured Workloads · Qatar Data Boundary · VPC Service Controls · CMEK (Cloud KMS) · IAM + per-agent service accounts · Access Transparency / Approval · Cloud Audit Logs'],
  ['Observability', 'Cloud Logging · Cloud Trace (OpenTelemetry from ADK) · Cloud Monitoring SLOs — first-token, p95 answer, scorer latency · BigQuery drift jobs · budgets & alerts'],
  ['Delivery', 'Terraform · Cloud Build CI/CD · adk eval release gate · Model Registry approvals · canary by Cloud Run traffic splitting · one container from Railway to Cloud Run'],
];

/* ───────────────────────────── Diagram ───────────────────────────── */
function DiagramView() {
  const [flowId, setFlowId] = useState('all');
  const [sel, setSel] = useState('mcp');
  const flow = FLOWS.find((f) => f.id === flowId);
  const inFlow = (id) => !flow.nodes || flow.nodes.includes(id);
  const node = BY_ID[sel];

  return (
    <div className="flex gap-2.5 h-full min-h-0">
      <div className="flex-1 min-w-0 flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3 px-1">
          <div className="seg-track" style={{ padding: 2 }}>
            {FLOWS.map((f) => (
              <button key={f.id} className={`seg-pill ${flowId === f.id ? 'active' : ''}`}
                style={{ fontSize: 10, padding: '4px 10px' }} onClick={() => setFlowId(f.id)}>{f.label}</button>
            ))}
          </div>
          <div className="flex items-center gap-3 text-[9.5px] font-semibold" style={{ color: 'var(--text-dim)' }}>
            {Object.entries(EDGE_STYLE).map(([k, st]) => (
              <span key={k} className="flex items-center gap-1.5">
                <svg width="26" height="8"><line x1="1" y1="4" x2="25" y2="4" stroke={st.color} strokeWidth={st.width + 0.6} strokeDasharray={st.dash} /></svg>
                {st.label}
              </span>
            ))}
          </div>
        </div>

        <div className="glass-card flex-1 min-h-0 p-2 overflow-auto">
          <svg viewBox={`0 0 ${W} ${HGT}`} width="100%" style={{ display: 'block', minWidth: 900 }}>
            <defs>
              {Object.entries(EDGE_STYLE).map(([k, st]) => (
                <marker key={k} id={`arr-${k}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                  <path d="M0,0 L10,5 L0,10 z" fill={st.color} />
                </marker>
              ))}
              <linearGradient id="lanehead" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0" stopColor="rgba(255,255,255,0.9)" /><stop offset="1" stopColor="rgba(255,255,255,0.55)" />
              </linearGradient>
            </defs>

            {/* lanes */}
            {LANES.map((l, i) => {
              const x = PAD + i * (LW + GAP);
              return (
                <g key={l.id}>
                  <rect x={x - 6} y={TOP - 8} width={LW + 12} height={BODY_BOTTOM - TOP + 8} rx="14"
                    fill="rgba(255,255,255,0.28)" stroke="rgba(15,23,42,0.05)" />
                  <rect x={x} y={8} width={LW} height={30} rx="9" fill="url(#lanehead)" stroke="rgba(15,23,42,0.07)" />
                  <rect x={x} y={8} width={5} height={30} rx="2.5" fill={LANE_TINT[i]} />
                  <text x={x + 14} y={21} fontSize="11" fontWeight="800" fill="#0a1628" fontFamily="Manrope, sans-serif">{l.title}</text>
                  <text x={x + 14} y={32.5} fontSize="8.2" fontWeight="600" fill="#64748b" fontFamily="Manrope, sans-serif">{l.sub}</text>
                </g>
              );
            })}

            {/* edges */}
            {EDGES.map(([a, b, kind]) => {
              const A = BY_ID[a], B = BY_ID[b], st = EDGE_STYLE[kind];
              const on = inFlow(a) && inFlow(b);
              const live = flowId !== 'all' && on;
              return (
                <path key={`${a}-${b}`} d={edgePath(A, B)} stroke={st.color} strokeWidth={live ? st.width + 0.8 : st.width}
                  strokeDasharray={live ? undefined : st.dash} markerEnd={`url(#arr-${kind})`}
                  className={`arch-edge ${on ? '' : 'dim'} ${live ? 'live' : ''}`} opacity={0.9} />
              );
            })}

            {/* nodes */}
            {NODES.map((n) => {
              const x = nx(n), y = ny(n), active = sel === n.id;
              return (
                <g key={n.id} className={`arch-node ${inFlow(n.id) ? '' : 'dim'}`} onClick={() => setSel(n.id)}>
                  <rect className="arch-node-box" x={x} y={y} width={LW} height={H} rx="10"
                    fill={active ? 'rgba(138,21,56,0.10)' : 'rgba(255,255,255,0.9)'}
                    stroke={active ? '#8A1538' : 'rgba(15,23,42,0.10)'} strokeWidth={active ? 1.8 : 1} />
                  <rect x={x} y={y + 8} width={4} height={H - 16} rx="2" fill={LANE_TINT[n.lane]} />
                  <foreignObject x={x + 4} y={y} width={LW - 6} height={H}>
                    <div xmlns="http://www.w3.org/1999/xhtml" className="arch-box">
                      <div className="l">{n.label}</div>
                      <div className="s">{n.sub}</div>
                    </div>
                  </foreignObject>
                </g>
              );
            })}

            {/* cross-cutting */}
            {XCUTS.map(([t, d], i) => {
              const y = XCUT_TOP + i * (XH + XG);
              return (
                <g key={t}>
                  <rect x={PAD} y={y} width={W - PAD * 2} height={XH} rx="8" fill="rgba(255,255,255,0.72)" stroke="rgba(138,21,56,0.14)" />
                  <foreignObject x={PAD} y={y} width={W - PAD * 2} height={XH}>
                    <div xmlns="http://www.w3.org/1999/xhtml" className="arch-xcut"><b>{t}</b><span>{d}</span></div>
                  </foreignObject>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* detail rail */}
      <div className="w-[330px] shrink-0 flex flex-col gap-2 min-h-0">
        {flow.story && (
          <div className="glass-card px-3.5 py-2.5">
            <p className="text-[8.5px] font-bold uppercase tracking-widest" style={{ color: EDGE_STYLE[flow.kind].color }}>{flow.label}</p>
            <p className="text-[10.5px] mt-1 leading-snug" style={{ color: 'var(--text-md)' }}>{flow.story}</p>
            <p className="text-[9.5px] mt-1.5 font-bold" style={{ color: 'var(--text)' }}>Budget · <span style={{ color: 'var(--brand)' }}>{flow.budget}</span></p>
          </div>
        )}
        <div className="glass-card flex-1 min-h-0 overflow-y-auto px-3.5 py-3">
          <p className="text-[8.5px] font-bold uppercase tracking-widest" style={{ color: LANE_TINT[node.lane] }}>{LANES[node.lane].title}</p>
          <h3 className="text-[14px] font-extrabold leading-tight mt-0.5" style={{ color: 'var(--text)' }}>{node.label}</h3>
          <p className="text-[9.5px] mt-0.5 mb-2" style={{ color: 'var(--text-dim)' }}>{node.sub}</p>
          {[['Why it is here', node.why], ['How it scales', node.scale], ['Alternative considered', node.alt],
            ['Phase 1 equivalent (running today)', node.p1], ['Cost', node.cost]].map(([k, v]) => (
            <div key={k} className="mb-2">
              <p className="text-[8.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-faint)' }}>{k}</p>
              <p className="text-[10.5px] leading-snug" style={{ color: 'var(--text-md)' }}>{v}</p>
            </div>
          ))}
          <p className="text-[9px] italic mt-2" style={{ color: 'var(--text-faint)' }}>Click any node. Region facts and list prices verified against Google Cloud pages on 7 Sep 2026.</p>
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────────── Flows ───────────────────────────── */
const MODE_STYLE = {
  'Real-time': ['badge-red', '#9b1c46'], 'Streaming export': ['badge-red', '#9b1c46'], 'Nightly batch': ['badge-amber', '#b8862e'],
  'Event-driven batch': ['badge-amber', '#b8862e'], Synchronous: ['badge-blue', '#6d4fa8'], 'Scheduled + triggered': ['badge-green', '#64748b'],
};
function FlowsView() {
  const rt = DATA_FLOWS.filter((f) => f.mode.startsWith('Real') || f.mode.startsWith('Streaming')).length;
  const batch = DATA_FLOWS.filter((f) => f.mode.includes('batch')).length;
  return (
    <div className="flex flex-col gap-2.5">
      <KpiStrip items={[
        { icon: 'activity', tone: 'maroon', label: 'Real-time paths (event-driven, seconds)', value: rt },
        { icon: 'coins', tone: 'gold', label: 'Batch paths (nightly / on upload)', value: batch },
        { icon: 'users', tone: 'violet', label: 'Synchronous, user-facing', value: 1 },
        { icon: 'gauge', tone: 'sand', label: 'Rule: stream per-patient, batch per-population', value: '1' },
      ]} />
      <Panel title="Every data path, its mode, and the reason it is not the other mode">
        <div className="px-1">
          <table className="w-full text-[10px]">
            <thead>
              <tr style={{ color: 'var(--text-faint)' }} className="text-left uppercase tracking-wider">
                <th className="py-1 font-bold">Flow</th><th className="font-bold">Mode</th><th className="font-bold">Transport</th>
                <th className="font-bold">Volume</th><th className="font-bold">Latency budget</th><th className="font-bold">Why this mode</th>
              </tr>
            </thead>
            <tbody>
              {DATA_FLOWS.map((f) => (
                <tr key={f.flow} className="border-t border-[rgba(15,23,42,0.05)] align-top" style={{ color: 'var(--text-md)' }}>
                  <td className="py-1.5 pr-2 font-bold" style={{ color: 'var(--text)', width: 190 }}>{f.flow}</td>
                  <td className="pr-2" style={{ width: 120 }}><span className={`badge ${MODE_STYLE[f.mode]?.[0] || 'badge-green'}`} style={{ fontSize: 8.5 }}>{f.mode}</span></td>
                  <td className="pr-2">{f.transport}</td>
                  <td className="pr-2" style={{ width: 120 }}>{f.volume}</td>
                  <td className="pr-2 font-semibold" style={{ width: 150, color: 'var(--brand)' }}>{f.latency}</td>
                  <td style={{ color: 'var(--text-dim)' }}>{f.why}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <div className="grid grid-cols-3 gap-2.5">
        {[
          ['The rule', 'Per-patient signals stream because a clinician acts on them the same day. Per-population metrics batch because they move over weeks and everyone must quote the same snapshot. Nothing is streamed because streaming is fashionable.'],
          ['What the user sees', 'Dashboards carry an as-of time. The agent says which numbers are live (risk of the patient in front of you) and which are the 02:00 snapshot (national control rate). Mixing the two silently is how trust is lost.'],
          ['What breaks first', 'Not throughput — a single scorer replica covers 50× the national peak. The failure modes are semantic: a late HL7v2 feed, a consent change not re-applied, drift in a lab analyser. Each has an alert on the Observability rail.'],
        ].map(([t, d]) => (
          <Panel key={t} title={t}><p className="px-2 text-[10.5px] leading-snug" style={{ color: 'var(--text-md)' }}>{d}</p></Panel>
        ))}
      </div>
    </div>
  );
}

/* ───────────────────────────── Scale & inference ───────────────────────────── */
function ScaleView() {
  return (
    <div className="flex flex-col gap-2.5">
      <KpiStrip items={[
        { icon: 'users', tone: 'maroon', label: 'Population in the national HIE', value: '3.0M' },
        { icon: 'activity', tone: 'gold', label: 'FHIR resource updates / day · peak 20/s', value: '≈ 500k' },
        { icon: 'gauge', tone: 'green', label: 'Scorer headroom — one replica vs national peak', value: '50×' },
        { icon: 'coins', tone: 'violet', label: 'Gemini prompt tokens / day at 20k questions', value: '≈ 77M' },
        { icon: 'heart', tone: 'sand', label: 'Availability target (3 zones, me-central1)', value: '99.9%' },
      ]} />
      <div className="grid grid-cols-12 gap-2.5">
        <div className="col-span-4">
          <Panel title="Planning assumptions">
            <div className="px-1 flex flex-col gap-1.5">
              {SCALE.assumptions.map(([k, v]) => (
                <div key={k} className="rounded-lg px-2.5 py-1.5" style={{ background: 'rgba(255,255,255,0.55)', border: '1px solid var(--hairline)' }}>
                  <p className="text-[8.5px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-faint)' }}>{k}</p>
                  <p className="text-[10.5px] font-semibold" style={{ color: 'var(--text)' }}>{v}</p>
                </div>
              ))}
            </div>
          </Panel>
        </div>
        <div className="col-span-8 flex flex-col gap-2.5">
          <Panel title="Inference — what runs where, and how fast">
            <div className="px-1">
              <table className="w-full text-[10px]">
                <thead>
                  <tr style={{ color: 'var(--text-faint)' }} className="text-left uppercase tracking-wider">
                    <th className="py-1 font-bold">Component</th><th className="font-bold">Model / method</th><th className="font-bold">Latency</th><th className="font-bold">Serving</th>
                  </tr>
                </thead>
                <tbody>
                  {SCALE.inference.map(([a, b, c, d]) => (
                    <tr key={a} className="border-t border-[rgba(15,23,42,0.05)] align-top" style={{ color: 'var(--text-md)' }}>
                      <td className="py-1.5 pr-2 font-bold" style={{ color: 'var(--text)' }}>{a}</td><td className="pr-2">{b}</td>
                      <td className="pr-2 font-semibold" style={{ color: 'var(--brand)' }}>{c}</td><td style={{ color: 'var(--text-dim)' }}>{d}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          <Panel title="How each layer scales — and what the real constraint is">
            <div className="px-1 grid grid-cols-2 gap-x-4 gap-y-1.5">
              {SCALE.scaling.map(([k, v]) => (
                <div key={k} className="text-[10px]">
                  <p className="font-extrabold" style={{ color: 'var(--text)' }}>{k}</p>
                  <p style={{ color: 'var(--text-dim)' }}>{v}</p>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
      <div className="glass-card px-4 py-2.5 text-[10.5px]" style={{ color: 'var(--text-md)' }}>
        <b style={{ color: 'var(--text)' }}>The honest scaling statement.</b> Compute is not the constraint anywhere in this design; the tabular model and BigQuery are embarrassingly over-provisioned at national scale.
        The two variables that actually drive cost and latency are Gemini tokens per question (topology, caching, thinking level) and the number of synchronous hops in a conversation — which is why the Evaluation tab measures both.
      </div>
    </div>
  );
}

/* ───────────────────────────── ADRs ───────────────────────────── */
function AdrsView() {
  const [open, setOpen] = useState(ADRS[0].id);
  return (
    <div className="grid grid-cols-12 gap-2.5">
      <div className="col-span-4 flex flex-col gap-1.5">
        {ADRS.map((a) => (
          <button key={a.id} onClick={() => setOpen(a.id)} className="text-left rounded-xl px-3 py-2 transition-all"
            style={{ background: open === a.id ? 'rgba(138,21,56,0.10)' : 'rgba(255,255,255,0.6)',
              border: `1px solid ${open === a.id ? 'rgba(138,21,56,0.35)' : 'var(--hairline)'}` }}>
            <p className="text-[8.5px] font-bold tracking-widest" style={{ color: 'var(--gold)' }}>{a.id}</p>
            <p className="text-[11px] font-extrabold leading-tight" style={{ color: 'var(--text)' }}>{a.title}</p>
          </button>
        ))}
      </div>
      <div className="col-span-8">
        {ADRS.filter((a) => a.id === open).map((a) => (
          <div key={a.id} className="glass-card px-5 py-4 h-full">
            <p className="text-[9px] font-bold tracking-widest" style={{ color: 'var(--gold)' }}>{a.id} · ACCEPTED</p>
            <h3 className="text-[16px] font-extrabold leading-tight mt-0.5 mb-3" style={{ color: 'var(--text)' }}>{a.title}</h3>
            {[['Decision', a.decision], ['Because', a.because], ['Consequences', a.consequences]].map(([k, v]) => (
              <div key={k} className="mb-3">
                <p className="text-[8.5px] font-bold uppercase tracking-widest mb-0.5" style={{ color: 'var(--text-faint)' }}>{k}</p>
                <p className="text-[11.5px] leading-relaxed" style={{ color: 'var(--text-md)' }}>{v}</p>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ───────────────────────────── Phases ───────────────────────────── */
function PhasesView() {
  return (
    <div className="flex flex-col gap-2.5">
      <Panel title="Phase 1 (Railway, running now) → Phase 2 (Google Cloud, me-central1) — same contracts, managed platform">
        <div className="px-1">
          <table className="w-full text-[10px]">
            <thead>
              <tr style={{ color: 'var(--text-faint)' }} className="text-left uppercase tracking-wider">
                <th className="py-1 font-bold" style={{ width: 110 }}>Capability</th><th className="font-bold">Phase 1 — this PoC</th>
                <th className="font-bold">Phase 2 — Google Cloud</th><th className="font-bold" style={{ width: 200 }}>What does not change</th>
              </tr>
            </thead>
            <tbody>
              {PHASES.map(([a, b, c, d]) => (
                <tr key={a} className="border-t border-[rgba(15,23,42,0.05)] align-top" style={{ color: 'var(--text-md)' }}>
                  <td className="py-1.5 pr-2 font-extrabold" style={{ color: 'var(--text)' }}>{a}</td>
                  <td className="pr-3" style={{ color: 'var(--text-dim)' }}>{b}</td>
                  <td className="pr-3 font-semibold">{c}</td>
                  <td className="font-semibold" style={{ color: 'var(--brand)' }}>{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <div className="grid grid-cols-3 gap-2.5">
        {[
          ['Why the PoC was built this way', 'Every phase-1 component was chosen to have a one-to-one managed equivalent. The container, the ADK agent tree, the MCP tool contracts, the feature function and the evalset all move unchanged; only the substrate under them changes.'],
          ['Migration order (12 weeks)', '1) Landing zone, Assured Workloads folder, VPC-SC, CMEK. 2) FHIR store + BigQuery streaming from a QHIE test feed. 3) Vertex pipeline, registry, endpoint, drift jobs. 4) ADK on Cloud Run + MCP servers + RAG Engine. 5) SSO, voice, write-back. 6) adk eval gate live in CI; pilot at 4 sites.'],
          ['What we would ask Google for', 'Agent Engine, Model Armor and Model Monitoring in me-central1 — the three managed services this design replaces with in-region equivalents. Each is a deploy-target change when it lands.'],
        ].map(([t, d]) => (
          <Panel key={t} title={t}><p className="px-2 text-[10.5px] leading-snug" style={{ color: 'var(--text-md)' }}>{d}</p></Panel>
        ))}
      </div>
    </div>
  );
}

/* ───────────────────────────── Cost ───────────────────────────── */
function CostView() {
  const pilot = COST.reduce((s, r) => s + r[1], 0);
  const national = COST.reduce((s, r) => s + r[2], 0);
  const bars = useMemo(() => [...COST].sort((a, b) => b[2] - a[2]).map((r) => ({ label: r[0].split(' (')[0], value: r[2] })), []);
  return (
    <div className="flex flex-col gap-2.5">
      <KpiStrip items={[
        { icon: 'coins', tone: 'gold', label: 'Pilot — 4 sites · 1k questions/day (USD / month)', value: `$${pilot.toLocaleString()}` },
        { icon: 'coins', tone: 'maroon', label: 'National — 18 facilities · 20k questions/day', value: `$${national.toLocaleString()}` },
        { icon: 'heart', tone: 'green', label: 'Avoided complication admissions that pay for the platform', value: (national / AVOIDED_ADMISSION_USD).toFixed(1), suffix: '/ month' },
        { icon: 'activity', tone: 'violet', label: 'Share of national cost that is Gemini tokens', value: `${Math.round((COST[0][2] / national) * 100)}%` },
      ]} />
      <div className="grid grid-cols-12 gap-2.5">
        <div className="col-span-7">
          <Panel title="Monthly run cost by component — order of magnitude at Doha list prices (Sept 2026)">
            <div className="px-1">
              <table className="w-full text-[10px]">
                <thead>
                  <tr style={{ color: 'var(--text-faint)' }} className="text-left uppercase tracking-wider">
                    <th className="py-1 font-bold">Component</th><th className="font-bold text-right">Pilot</th><th className="font-bold text-right">National</th><th className="font-bold pl-3">Basis</th>
                  </tr>
                </thead>
                <tbody>
                  {COST.map(([n, a, b, note]) => (
                    <tr key={n} className="border-t border-[rgba(15,23,42,0.05)]" style={{ color: 'var(--text-md)' }}>
                      <td className="py-1 font-semibold" style={{ color: 'var(--text)' }}>{n}</td>
                      <td className="text-right">{a ? `$${a.toLocaleString()}` : '—'}</td>
                      <td className="text-right font-bold">${b.toLocaleString()}</td>
                      <td className="pl-3" style={{ color: 'var(--text-faint)' }}>{note}</td>
                    </tr>
                  ))}
                  <tr className="border-t-2 border-[rgba(138,21,56,0.25)] font-extrabold" style={{ color: 'var(--text)' }}>
                    <td className="py-1.5">Total</td><td className="text-right">${pilot.toLocaleString()}</td><td className="text-right" style={{ color: 'var(--brand)' }}>${national.toLocaleString()}</td><td />
                  </tr>
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
        <div className="col-span-5 flex flex-col gap-2.5">
          <div style={{ height: 280 }}>
            <Panel title="National monthly cost by component (USD / month)"><Bar3D data={bars} ramp={1} maxBars={9} /></Panel>
          </div>
          <Panel title="How to read this">
            <ul className="px-2 ml-3 list-disc text-[10px] flex flex-col gap-1" style={{ color: 'var(--text-md)' }}>
              <li>List prices, no committed-use discounts, no Google credits. Real numbers come from a Billing export after the pilot month.</li>
              <li>Tokens dominate and are the only line that scales with conversations. Intro pricing ends Dec 2026; the 2027 figure is on the Evaluation tab.</li>
              <li>One avoided complication admission ≈ QAR 32,000 (≈ ${AVOIDED_ADMISSION_USD.toLocaleString()}). The national platform costs about {(national / AVOIDED_ADMISSION_USD).toFixed(1)} of them a month; the statin programme alone is modelled to avoid far more (Cost & Equity dashboard).</li>
              <li>Excludes: MOPH staff, site VPNs, Looker licences, and the QHIE side.</li>
            </ul>
          </Panel>
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────────── page ───────────────────────────── */
export default function ArchitecturePage() {
  const [view, setView] = useState('diagram');
  const sub = {
    diagram: 'Six lanes, four kinds of arrows. Click a node for why it is there, how it scales, what was rejected, what runs today in phase 1 and what it costs.',
    flows: 'Per-patient signals stream; per-population metrics batch. Every path with its transport, volume, latency budget and the reason for its mode.',
    scale: 'Planning numbers for 3M patients and 20k questions a day, and where inference actually runs.',
    adrs: 'Ten architecture decision records — decision, reasoning, consequences. Including the ones where Doha regional availability forced a different answer.',
    phases: 'What changes between the Railway PoC and the Google Cloud deployment, and what deliberately does not.',
    cost: 'Order-of-magnitude monthly run cost at Doha list prices, pilot and national, against the cost of one avoided admission.',
  }[view];

  return (
    <div className={`h-full p-3 flex flex-col gap-2.5 ${view === 'diagram' ? 'overflow-hidden' : 'overflow-y-auto'}`}>
      <div className="flex items-end justify-between px-1 shrink-0">
        <div>
          <h1 className="text-[17px] font-extrabold tracking-tight leading-none" style={{ color: 'var(--text)' }}>
            Architecture — deploy, not demo
          </h1>
          <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>{sub}</p>
        </div>
        <div className="seg-track">
          {VIEWS.map(([k, l]) => (
            <button key={k} className={`seg-pill ${view === k ? 'active' : ''}`} onClick={() => setView(k)}>{l}</button>
          ))}
        </div>
      </div>
      <div className={view === 'diagram' ? 'flex-1 min-h-0' : ''}>
        {view === 'diagram' && <DiagramView />}
        {view === 'flows' && <FlowsView />}
        {view === 'scale' && <ScaleView />}
        {view === 'adrs' && <AdrsView />}
        {view === 'phases' && <PhasesView />}
        {view === 'cost' && <CostView />}
      </div>
    </div>
  );
}
