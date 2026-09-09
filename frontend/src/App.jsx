import { useEffect, useState } from 'react';
import { AppProvider, PERSONAS, useApp } from './context/AppContext';
import { getHealth } from './services/api';
import LandingPage from './pages/LandingPage';
import AssistantPage from './pages/AssistantPage';
import DashboardOverview from './pages/DashboardOverview';
import DashboardClinical from './pages/DashboardClinical';
import DashboardRisk from './pages/DashboardRisk';
import DashboardCost from './pages/DashboardCost';
import DashboardMap from './pages/DashboardMap';
import QueuePage from './pages/QueuePage';
import DocumentsPage from './pages/DocumentsPage';
import DataPage from './pages/DataPage';
import AuditPage from './pages/AuditPage';
import ArchitecturePage from './pages/ArchitecturePage';
import EvaluationPage from './pages/EvaluationPage';

const DASH_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'clinical', label: 'Clinical Quality' },
  { id: 'risk', label: 'Risk & Models' },
  { id: 'cost', label: 'Cost & Equity' },
  { id: 'geography', label: 'Geography' },
];
const DASH_IDS = DASH_TABS.map((t) => t.id);

function Bokeh() {
  return (
    <div className="bokeh-layer">
      <div className="bokeh-dot mega-blue a1" /><div className="bokeh-dot mega-cyan a2" />
      <div className="bokeh-dot mega-purple a3" /><div className="bokeh-dot mega-amber a4" />
      <div className="bokeh-dot mega-cyan a5" />
      <div className="bokeh-dot blue-blob m1" /><div className="bokeh-dot cyan-blob m2" />
      <div className="bokeh-dot blue-blob m3" /><div className="bokeh-dot cyan-blob m4" />
      <div className="bokeh-dot blue-blob m5" /><div className="bokeh-dot purple-blob m6" />
      <div className="bokeh-dot blue-blob m7" /><div className="bokeh-dot amber-blob m8" />
      <div className="bokeh-dot cyan-blob m9" /><div className="bokeh-dot blue-blob m10" />
    </div>
  );
}

/** Persona picker — the Roads TargetSelector recipe (light glass dropdown). */
function PersonaSelector() {
  const { persona, setPersona, personaInfo } = useApp();
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-2 pl-3 pr-2.5 py-1.5 rounded-lg text-[12px] font-semibold transition-all"
        style={{
          background: 'rgba(255,255,255,0.65)', backdropFilter: 'blur(12px)',
          border: '1px solid rgba(138,21,56,0.22)', color: 'var(--text)', minWidth: 210,
        }}>
        <span className="w-2 h-2 rounded-full shrink-0" style={{ background: 'var(--green)' }} />
        <span className="flex-1 text-left truncate">{personaInfo.name}</span>
        <span className="text-[8.5px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded shrink-0"
          style={{ background: 'rgba(138,21,56,0.10)', color: 'var(--brand)' }}>
          {persona}
        </span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" strokeWidth="2.5"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 rounded-xl shadow-xl overflow-hidden z-50 w-[280px] animate-fade-up"
            style={{ background: 'rgba(255,255,255,0.97)', border: '1px solid rgba(138,21,56,0.2)', backdropFilter: 'blur(20px)' }}>
            <p className="px-3 pt-2.5 pb-1 text-[9px] font-bold tracking-widest uppercase" style={{ color: 'var(--text-dim)' }}>
              Personas
            </p>
            <div className="pb-1.5">
              {Object.values(PERSONAS).map((u) => {
                const active = u.id === persona;
                return (
                  <button key={u.id} onClick={() => { setPersona(u.id); setOpen(false); }}
                    className="w-full text-left px-3 py-2 transition-all hover:bg-[rgba(138,21,56,0.06)] flex items-center gap-2.5"
                    style={active ? { background: 'rgba(138,21,56,0.10)', borderLeft: '3px solid var(--brand)' }
                      : { borderLeft: '3px solid transparent' }}>
                    <div className={`w-7 h-7 rounded-full ${u.color} flex items-center justify-center text-white text-[10px] font-bold shrink-0`}>
                      {u.avatar}
                    </div>
                    <div className="min-w-0">
                      <p className="text-[12px] font-semibold truncate" style={{ color: active ? 'var(--brand-lo)' : 'var(--text)' }}>{u.name}</p>
                      <p className="text-[10.5px] truncate" style={{ color: 'var(--text-dim)' }}>{u.sub}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Header({ tab, setTab }) {
  const [health, setHealth] = useState(null);
  useEffect(() => {
    let timer;
    const tick = () => getHealth().then((h) => {
      setHealth(h);
      // keep polling until the agent graph has warmed up (or the key has failed)
      if (h?.mode === 'multi-agent' && !h.warmup?.ready) timer = setTimeout(tick, 3000);
    }).catch(() => setHealth({ status: 'down' }));
    tick();
    return () => clearTimeout(timer);
  }, []);
  const ok = health?.status === 'ok';
  const selfTest = health?.warmup?.self_test;
  const warming = ok && health.mode === 'multi-agent' && !health.warmup?.ready;
  const keyBad = ok && health.mode === 'multi-agent' && selfTest && !selfTest.ok;
  const switched = health?.model_switches?.length ? health.model_switches[health.model_switches.length - 1] : null;

  const tabs = [
    { id: 'landing', label: 'Home' },
    { id: 'assistant', label: 'Assistant' },
    { id: 'overview', label: 'Dashboards' },
    { id: 'architecture', label: 'Architecture' },
    { id: 'evaluation', label: 'AI Evaluation' },
    { id: 'queue', label: 'Queue' },
    { id: 'documents', label: 'Documents' },
    { id: 'data', label: 'Data' },
    { id: 'audit', label: 'Audit' },
  ];
  const isDash = DASH_IDS.includes(tab);
  const activeTop = isDash ? 'overview' : tab;

  return (
    <header className="app-header">
      <button onClick={() => setTab('landing')}>
        <img className="brand-logo" src="/google-g.svg" alt="Google" />
      </button>

      <div className="title-block">
        <div className="header-eyebrow">
          {health?.platform?.compute === 'cloud-run'
            ? `Google Cloud · Cloud Run ${health.platform.region || 'me-central1'} · BigQuery ${health.platform.data?.dataset || ''} · Vertex AI Gemini · Qatar HIE`
            : 'Google Cloud · Doha region (me-central1) · Qatar Health Information Exchange'}
        </div>
        <div className="title-row">
          <h1 className="app-title">
            <b>Nabd</b> <span className="title-ar">نبض</span> — Population Health Intelligence
          </h1>
          <div className="accent-line" />
        </div>
        <div className="nav-row">
          <div className="seg-track">
            {tabs.map((t) => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`seg-pill ${activeTop === t.id ? 'active' : ''}`}>
                {t.label}
              </button>
            ))}
          </div>
          {isDash && (
            <>
              <span className="nav-divider" />
              <div className="seg-track">
                {DASH_TABS.map((t) => (
                  <button key={t.id} onClick={() => setTab(t.id)}
                    className={`seg-pill ${tab === t.id ? 'active' : ''}`}>
                    {t.label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="status-pill">
          <span className={`w-2 h-2 rounded-full ${ok && !warming && !keyBad ? '' : 'animate-pulse'}`}
            style={{ background: !ok ? (health ? 'var(--red)' : 'var(--amber)') : keyBad ? 'var(--red)' : warming ? 'var(--amber)' : 'var(--green)' }} />
          <span title={keyBad ? selfTest.error : undefined}>
            {health == null ? 'Connecting…'
              : !ok ? 'Backend offline'
              : health.mode !== 'multi-agent' ? '6 agents · MCP · scripted engine'
              : warming ? '6 agents · MCP · warming up…'
              : keyBad ? (selfTest.capacity
                  ? `Gemini at capacity (503) — retrying every minute · scripted chips still work`
                  : `Gemini key rejected — scripted chips still work`)
              : `6 agents · MCP · ${health.model}${switched ? ` (fell back from ${switched.from})` : ''}`}
          </span>
        </div>
        <PersonaSelector />
      </div>
    </header>
  );
}

function Layout() {
  const [tab, setTab] = useState('landing');
  const page = () => {
    switch (tab) {
      case 'landing': return <LandingPage go={setTab} />;
      case 'assistant': return <AssistantPage />;
      case 'overview': return <DashboardOverview />;
      case 'clinical': return <DashboardClinical />;
      case 'risk': return <DashboardRisk />;
      case 'cost': return <DashboardCost />;
      case 'geography': return <DashboardMap />;
      case 'architecture': return <ArchitecturePage />;
      case 'evaluation': return <EvaluationPage />;
      case 'queue': return <QueuePage />;
      case 'documents': return <DocumentsPage />;
      case 'data': return <DataPage />;
      case 'audit': return <AuditPage />;
      default: return <LandingPage go={setTab} />;
    }
  };

  return (
    <div className="app-shell">
      <Bokeh />
      <Header tab={tab} setTab={setTab} />
      <main className="flex-1 min-h-0 relative z-[1]">
        {page()}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <Layout />
    </AppProvider>
  );
}
