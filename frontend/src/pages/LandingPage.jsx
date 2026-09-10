import { useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext';
import { getDashboard, getDataTables, getStoryHero } from '../services/api';
import { Bar3D } from '../components/Chart3D';
import { AgentChip, KpiStrip } from '../components/ui';

/* ─── count-up hook (ease-out) ─── */
function useCountUp(target, duration = 1700, start = true) {
  const [v, setV] = useState(0);
  const raf = useRef(null);
  useEffect(() => {
    if (!start || target == null) return;
    const t0 = performance.now();
    const tick = (t) => {
      const p = Math.min(1, (t - t0) / duration);
      const e = 1 - Math.pow(1 - p, 3);
      setV(target * e);
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [target, duration, start]);
  return v;
}

function Counter({ value, format, label }) {
  const v = useCountUp(value);
  return (
    <div>
      <div className="counter-val">{value == null ? 'n/a' : format(v)}</div>
      <div className="counter-lbl">{label}</div>
    </div>
  );
}

/* ─── The ECG: a synthetic normal-sinus trace, drawn on loop ─── */
const ECG_D = (() => {
  const beat = (x) => `L${x} 80 L${x + 14} 80 L${x + 20} 70 L${x + 26} 80 L${x + 40} 80 L${x + 46} 84 L${x + 50} 22 L${x + 55} 108 L${x + 60} 80 L${x + 78} 80 L${x + 90} 66 L${x + 102} 80`;
  return `M0 80 ${beat(20)} ${beat(170)} ${beat(320)} ${beat(470)} L640 80`;
})();

const AGENTS = [
  { id: 'cohort_agent', name: 'Cohort', sub: 'HIE QUERIES', color: '#8a6a4e' },
  { id: 'guideline_agent', name: 'Guidelines', sub: 'RAG · CITATIONS', color: '#3a8e5a' },
  { id: 'risk_agent', name: 'Risk · ML', sub: 'SCORE · SIMULATE', color: '#b06024' },
  { id: 'pophealth_agent', name: 'Pop-health', sub: 'MCP SERVER ★', color: '#b8862e', mcp: true },
  { id: 'action_agent', name: 'Actions', sub: 'HUMAN-IN-LOOP', color: '#9b1c46' },
];

function Constellation() {
  const cx = 260, cy = 176, R = 128;
  const nodes = AGENTS.map((a, i) => {
    const ang = (-90 + i * 72) * (Math.PI / 180);
    return { ...a, x: cx + R * Math.cos(ang), y: cy + R * Math.sin(ang) };
  });
  return (
    <svg viewBox="0 0 520 352" style={{ width: '100%', height: 'auto', overflow: 'visible' }}>
      <defs>
        <linearGradient id="core-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#ad3a5c" /><stop offset="1" stopColor="#4a0c20" />
        </linearGradient>
      </defs>
      {nodes.map((n) => (
        <line key={`l-${n.id}`} x1={cx} y1={cy} x2={n.x} y2={n.y} className={`cst-link ${n.mcp ? 'gold' : ''}`} />
      ))}
      <g className="cst-node">
        <circle cx={cx} cy={cy} r="50" className="cst-core" />
        <text x={cx} y={cy - 4} className="cst-core-text">Supervisor</text>
        <text x={cx} y={cy + 11} className="cst-core-sub">LLM · ADK</text>
      </g>
      {nodes.map((n) => (
        <g key={n.id} className="cst-node">
          {n.mcp && <circle cx={n.x} cy={n.y} r="44" className="cst-ring" />}
          <circle cx={n.x} cy={n.y} r="36" className="body" stroke={n.color} />
          <text x={n.x} y={n.y - 1} className="lbl">{n.name}</text>
          <text x={n.x} y={n.y + 12} className="sub">{n.sub}</text>
        </g>
      ))}
    </svg>
  );
}

function RiskRing({ pct }) {
  const r = 34, c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 90 90" style={{ width: 96, height: 96 }}>
      <circle cx="45" cy="45" r={r} fill="none" stroke="rgba(15,23,42,0.08)" strokeWidth="9" />
      <circle cx="45" cy="45" r={r} fill="none" stroke="url(#risk-grad)" strokeWidth="9" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - pct)} transform="rotate(-90 45 45)"
        style={{ transition: 'stroke-dashoffset 1.4s cubic-bezier(0.34,1.1,0.64,1)' }} />
      <defs>
        <linearGradient id="risk-grad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#b8862e" /><stop offset="1" stopColor="#8A1538" />
        </linearGradient>
      </defs>
      <text x="45" y="52" className="risk-ring-val">{Math.round(pct * 100)}%</text>
    </svg>
  );
}

export default function LandingPage({ go }) {
  const { personaInfo } = useApp();
  const [ov, setOv] = useState(null);
  const [tables, setTables] = useState(null);
  const [risk, setRisk] = useState(null);
  const [hero, setHero] = useState(null);

  useEffect(() => {
    getDashboard('overview').then(setOv).catch(() => {});
    getDataTables().then((r) => setTables(r.tables)).catch(() => {});
    getDashboard('risk').then(setRisk).catch(() => {});
    getStoryHero().then(setHero).catch(() => {});
  }, []);

  const rows = (name) => tables?.find((t) => t.name === name)?.rows;
  const kpi = ov?.kpis || [];
  const patients = rows('patients');
  const obs = rows('observations');
  const enc = rows('encounters');
  const gaps = rows('care_gaps');
  const costM = ov ? parseFloat(kpi[5]?.value) : null;
  const overdue = ov ? kpi[4]?.value : null;
  const auc = risk?.auc, legacy = risk?.legacy_auc;
  const p = hero?.patient;

  return (
    <div className="landing">
      <div className="landing-inner">

        {/* ── HERO ── */}
        <section className="hero">
          <img src="/nabd-mark.svg" alt="" className="hero-g" />
          <div className="relative z-[1]">
            <div className="section-eyebrow reveal d1">National diabetes registry · Qatar Health Information Exchange</div>
            <h1 className="hero-title reveal d2">
              Diabetes population health,<br />
              <span className="hero-grad">answered from the exchange.</span>
            </h1>
            <p className="hero-lede mt-5 reveal d3">
              Nabd sits on Qatar's Health Information Exchange. Clinicians and ministry leaders ask questions in
              plain language; a supervisor agent routes each question to specialist agents that query the exchange,
              cite the national diabetes guidelines, run the deterioration-risk model and draft actions for a clinician
              to approve. Every answer is traceable to the data row and the guideline page.
            </p>
            <div className="flex items-center gap-3 mt-7 reveal d4">
              <button className="btn-primary" onClick={() => go('assistant')}>Open the Assistant</button>
              <button className="btn-secondary" onClick={() => go('overview')}>Registry dashboards</button>
            </div>
            <p className="text-[11px] mt-5 reveal d5" style={{ color: 'var(--text-faint)' }}>
              Agent Development Kit · Model Context Protocol · cited guideline retrieval · Target platform: Google Cloud, me-central1 (Doha)
            </p>
          </div>

          <div className="relative z-[1] reveal d3">
            <div className="glass-card p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="ecg-live">Live · registry summary</span>
                <span className="text-[10px] font-bold" style={{ color: 'var(--text-faint)' }}>36 months · 8 tables · FHIR R4 export</span>
              </div>
              <div className="ecg-wrap">
                <svg viewBox="0 0 640 160" style={{ width: '100%', height: '100%' }} preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="ecg-grad" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0" stopColor="#8A1538" /><stop offset="0.6" stopColor="#b8862e" /><stop offset="1" stopColor="#d4a64f" />
                    </linearGradient>
                  </defs>
                  <path d={ECG_D} className="ecg-base" />
                  <path d={ECG_D} className="ecg-path" />
                </svg>
              </div>
              <div className="grid grid-cols-4 gap-3 mt-2 pt-4 border-t border-[rgba(15,23,42,0.07)]">
                <Counter value={patients} format={(v) => Math.round(v).toLocaleString()} label="Patients" />
                <Counter value={obs} format={(v) => `${(v / 1000).toFixed(0)}k`} label="Observations" />
                <Counter value={enc} format={(v) => `${(v / 1000).toFixed(0)}k`} label="Encounters" />
                <Counter value={costM} format={(v) => `${v.toFixed(1)}M`} label="QAR / year" />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-3 justify-end">
              <span className="badge badge-red">{overdue ?? 'n/a'} HbA1c tests overdue</span>
              <span className="badge badge-amber">{gaps?.toLocaleString() ?? 'n/a'} open care gaps</span>
              <span className="badge badge-green">Synthetic data · no PHI</span>
            </div>
          </div>
        </section>

        {ov && <KpiStrip items={kpi.map((k, i) => ({
          ...k, icon: ['users', 'droplet', 'check', 'alert', 'activity', 'coins'][i],
          tone: ['sand', 'rose', 'green', 'maroon', 'red', 'gold'][i],
        }))} />}

        {/* ── AGENTS ── */}
        <section className="landing-section grid grid-cols-2 gap-10 items-center">
          <div>
            <div className="section-eyebrow">Prototype orchestration pattern · Google Agent Development Kit</div>
            <h2 className="section-title">A supervisor and five specialists,<br />with a complete audit trail.</h2>
            <p className="section-sub mt-3">
              The orchestration pattern used in this prototype. The supervisor plans and composes; it does not invent figures. The data specialist queries the exchange,
              the guideline specialist retrieves and cites, the risk specialist runs the deployed models, the
              population-health specialist works through the MCP server, and the action specialist drafts review tasks, recalls and referrals into a queue
              that a clinician must approve. The production topology is benchmarked against the customer's evalset during discovery.
            </p>
            <div className="mt-5 space-y-3">
              {[
                ['The question', 'is asked in English or Arabic, typed or spoken.'],
                ['The supervisor plans', 'and routes to the specialists it needs; each step is shown as it happens.'],
                ['Tools do the work', 'exchange queries, guideline retrieval, model scoring, an MCP call, a draft.'],
                ['The answer is cited', 'with charts, guideline pages, and any action waiting for approval.'],
              ].map(([t, d], i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className="step-num">{i + 1}</span>
                  <p className="text-[12.5px] leading-relaxed" style={{ color: 'var(--text-md)' }}>
                    <b style={{ color: 'var(--text)' }}>{t}</b>: {d}
                  </p>
                </div>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5 mt-5">
              {['nabd_supervisor', ...AGENTS.map((a) => a.id)].map((a) => <AgentChip key={a} agent={a} />)}
            </div>
          </div>
          <div className="glass-card p-6">
            <Constellation />
            <p className="text-[10.5px] text-center mt-2" style={{ color: 'var(--text-faint)' }}>
              The population-health specialist connects over the Model Context Protocol to a server built for this programme: care gaps, quality measures, stratification and predictive risk scenarios.
            </p>
          </div>
        </section>

        {/* ── MODELS ── */}
        <section className="landing-section grid grid-cols-2 gap-10 items-center">
          <div className="glass-card p-5" style={{ height: 330 }}>
            <p className="panel-title mb-2">Deterioration-risk model · held-out AUC</p>
            {auc && (
              <Bar3D data={[{ label: 'Registry rule-based tier', value: +(legacy * 100).toFixed(1) },
                            { label: 'Nabd XGBoost', value: +(auc * 100).toFixed(1) }]} unit="%" />
            )}
          </div>
          <div>
            <div className="section-eyebrow">Machine learning · evaluated on held-out patients</div>
            <h2 className="section-title">Four models trained on the exchange.<br />The deterioration model outperforms the registry tier by {auc && legacy ? `${((auc - legacy) * 100).toFixed(1)} points` : '…'}.</h2>
            <p className="section-sub mt-3">
              The deterioration-risk model learns what the rule-based registry tier cannot see: kidney function, the
              HbA1c trajectory, adherence, missed monitoring and complication status. Every score is explained with
              feature contributions, and monotonic clinical constraints keep those explanations plausible. The same
              model drives two simulators: the programme simulator re-scores an eligible cohort with an intervention
              applied, and the patient simulator lets a clinician move a lever and watch the estimate respond.
            </p>
            <button className="btn-secondary mt-4" onClick={() => go('simulator')}>Open the risk simulator</button>
            <div className="grid grid-cols-2 gap-2.5 mt-5">
              {(risk?.model_cards || []).map((c) => (
                <div key={c.model_id} className="model-card">
                  <p className="text-[12px] font-extrabold" style={{ color: 'var(--text)' }}>{c.name}</p>
                  <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-dim)' }}>{c.framework}</p>
                  <span className="badge badge-blue mt-2">v{c.version}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── THE STORY ── */}
        <section className="landing-section">
          <div className="section-eyebrow">The patient the demonstration follows</div>
          <h2 className="section-title">{p ? p.full_name : 'A patient'}: flagged by the model, not by the registry tier.</h2>
          <div className="grid grid-cols-[1.2fr_1fr] gap-6 mt-5 items-stretch">
            <div className="glass-card p-5 flex gap-5 items-center">
              <div className="w-16 h-16 rounded-2xl shrink-0 flex items-center justify-center text-white text-[18px] font-extrabold"
                style={{ background: 'var(--brand-grad)', boxShadow: '0 8px 20px rgba(138,21,56,0.3)' }}>
                {p ? p.full_name.split(' ').map((w) => w[0]).join('').slice(0, 2) : 'n/a'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[16px] font-extrabold" style={{ color: 'var(--text)' }}>
                  {p?.full_name ?? 'Loading…'} <span className="text-[12px] font-semibold" style={{ color: 'var(--text-dim)' }}>{p ? `· ${p.age}, ${p.nationality}, ${p.facility_name}` : ''}</span>
                </p>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {(hero?.conditions || []).slice(0, 6).map((c) => <span key={c.condition} className="chip-cond">{c.condition}</span>)}
                </div>
                <div className="grid grid-cols-4 gap-3 mt-3">
                  {[['HbA1c', p ? `${p.hba1c_latest}%` : 'n/a'], ['HbA1c 12 mo ago', p ? `${p.hba1c_12m_ago ?? 'n/a'}%` : 'n/a'],
                    ['BMI · eGFR', p ? `${p.bmi} · ${Math.round(p.egfr_latest)}` : 'n/a'], ['Registry tier', p ? p.registry_risk_tier : 'n/a']].map(([k, v]) => (
                    <div key={k}>
                      <p className="text-[9px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-faint)' }}>{k}</p>
                      <p className="text-[14px] font-extrabold" style={{ color: 'var(--text)' }}>{v}</p>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {(p?.open_care_gaps || '').split(';').filter(Boolean).map((g) => (
                    <span key={g} className="chip-gap">{g.replace(/_/g, ' ')}</span>
                  ))}
                </div>
              </div>
              <div className="text-center shrink-0">
                <RiskRing pct={hero?.risk?.event_probability_12m ?? 0} />
                <p className="text-[9px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-faint)' }}>12-mo deterioration risk</p>
              </div>
            </div>
            <div className="glass-card p-5 flex flex-col justify-between">
              <div>
                <p className="text-[12.5px] leading-relaxed" style={{ color: 'var(--text-md)' }}>
                  {p ? (
                    <>HbA1c has risen from <b>{p.hba1c_12m_ago ?? 'n/a'}%</b> to <b>{p.hba1c_latest}%</b> in twelve months on <b>metformin alone</b>
                    {p.ckd || p.albuminuria ? <>, with early kidney involvement (eGFR {Math.round(p.egfr_latest)})</> : <>, with a BMI of {p.bmi}</>}.
                    The registry's rule-based tier lists {p.gender === 'female' ? 'her' : 'him'} as <b>{p.registry_risk_tier}</b>. The deterioration model puts the 12-month
                    risk at <b>{Math.round((hero?.risk?.event_probability_12m ?? 0) * 100)}%</b>, and the cited national guideline covers therapy intensification at this point.
                    Nabd surfaces the case, cites the guideline page, and drafts a clinical review task for Dr. Al-Mansoori to approve; the treatment decision is hers.</>
                  ) : 'Loading the case…'}
                </p>
              </div>
              <button className="btn-primary mt-4 self-start" onClick={() => go('assistant')}>Open the case in the Assistant</button>
            </div>
          </div>
        </section>

        {/* ── BUILT ON GOOGLE ── */}
        <section className="landing-section pb-8">
          <div className="section-eyebrow">Target platform: Google Cloud</div>
          <h2 className="section-title">The agent stack in this demonstration, and the Google Cloud services it maps to in Doha.</h2>
          <div className="text-[10px] font-bold uppercase tracking-[0.14em] mt-4 mb-1.5" style={{ color: 'var(--text-faint)' }}>In this demonstration</div>
          <div className="flex flex-wrap gap-2">
            {[['Agent Development Kit', '#8A1538'], ['Model Context Protocol', '#b8862e'], ['Function-calling LLM supervisor', '#8A1538'],
              ['Guideline retrieval · page-level citations', '#8A1538'], ['XGBoost risk model · v2.2.0', '#8a6a4e'], ['Web Speech · EN/AR', '#8a6a4e']].map(([n, c]) => (
              <span key={n} className="gcloud-chip"><span className="dot" style={{ background: c }} />{n}</span>
            ))}
          </div>
          <div className="text-[10px] font-bold uppercase tracking-[0.14em] mt-4 mb-1.5" style={{ color: 'var(--text-faint)' }}>Target architecture on Google Cloud, me-central1, to validate in discovery</div>
          <div className="flex flex-wrap gap-2">
            {['Cloud Healthcare API · FHIR R4', 'BigQuery · BigQuery ML', 'Vertex AI endpoint', 'RAG Engine',
              'Cloud Run', 'AlloyDB', 'Assured Workloads · Qatar Data Boundary'].map((n) => (
              <span key={n} className="gcloud-chip target"><span className="dot" style={{ background: '#94a3b8' }} />{n}</span>
            ))}
          </div>
          <p className="text-[10.5px] mt-6" style={{ color: 'var(--text-faint)' }}>
            Signed in as {personaInfo.name}. Switch persona at the top right. All patient data is synthetic and not for clinical use.
          </p>
        </section>
      </div>
    </div>
  );
}
