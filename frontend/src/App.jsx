import { useState } from 'react';
import { AppProvider, PERSONAS, useApp } from './context/AppContext';
import LandingPage from './pages/LandingPage';
import AssistantPage from './pages/AssistantPage';
import DashboardOverview from './pages/DashboardOverview';
import DashboardClinical from './pages/DashboardClinical';
import DashboardRisk from './pages/DashboardRisk';
import DashboardCost from './pages/DashboardCost';
import QueuePage from './pages/QueuePage';
import DocumentsPage from './pages/DocumentsPage';
import DataPage from './pages/DataPage';
import AuditPage from './pages/AuditPage';

const DASH_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'clinical', label: 'Clinical Quality' },
  { id: 'risk', label: 'Risk & Models' },
  { id: 'cost', label: 'Cost & Equity' },
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

function TopNav({ tab, setTab }) {
  const { persona, setPersona, personaInfo } = useApp();
  const [open, setOpen] = useState(false);
  const tabs = [
    { id: 'landing', label: 'Home' },
    { id: 'assistant', label: 'Assistant' },
    { id: 'overview', label: 'Dashboards' },
    { id: 'queue', label: 'Queue' },
    { id: 'documents', label: 'Documents' },
    { id: 'data', label: 'Data' },
    { id: 'audit', label: 'Audit' },
  ];
  const activeTop = DASH_IDS.includes(tab) ? 'overview' : tab;

  return (
    <nav className="flex items-center h-[54px] px-6 relative z-[200] shrink-0"
      style={{ background: 'var(--nav-grad)', boxShadow: '0 2px 20px rgba(0,0,0,0.35)' }}>
      <button className="flex items-center gap-2.5 mr-8 shrink-0" onClick={() => setTab('landing')}>
        <img src="/nabd-mark.svg" alt="Nabd" className="h-8 w-8" />
        <div className="flex flex-col leading-tight text-left">
          <span className="text-[13px] font-extrabold text-white tracking-wide">Nabd <span className="font-normal opacity-70">نبض</span></span>
          <span className="text-[8.5px] text-white/60 tracking-[0.2em] uppercase">Population Health Intelligence</span>
        </div>
      </button>

      <div className="flex gap-1">
        {tabs.map((t) => {
          const active = activeTop === t.id;
          return (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`relative px-3.5 py-1.5 rounded-lg text-[12px] font-semibold tracking-wide transition-all ${
                active ? 'text-white bg-white/[0.12]' : 'text-white/70 hover:text-white hover:bg-white/[0.06]'
              }`}>
              {t.label}
              {active && (
                <span className="absolute -bottom-[13px] left-3 right-3 h-[2px] rounded"
                  style={{ background: 'var(--brand-hi)', boxShadow: '0 0 10px rgba(66,133,244,0.8)' }} />
              )}
            </button>
          );
        })}
      </div>

      <div className="flex-1" />

      <div className="hidden lg:flex items-center gap-2 mr-4">
        <span className="w-2 h-2 rounded-full" style={{ background: '#34a853', animation: 'pulse-dot 2.4s infinite' }} />
        <span className="text-[10px] text-white/60 font-semibold tracking-wide">6 AGENTS ONLINE · MCP CONNECTED</span>
      </div>

      {/* Persona switcher */}
      <div className="relative">
        <button onClick={() => setOpen(!open)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/5 transition-all">
          <div className={`w-7 h-7 rounded-full ${personaInfo.color} flex items-center justify-center text-white text-[10px] font-bold`}>
            {personaInfo.avatar}
          </div>
          <div className="flex flex-col leading-tight items-start">
            <span className="text-white/90 text-[11.5px] font-medium">{personaInfo.name}</span>
            <span className="text-white/45 text-[9px]">{personaInfo.sub}</span>
          </div>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="2">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        {open && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
            <div className="absolute top-full right-0 mt-1 rounded-xl overflow-hidden z-50 min-w-[250px] animate-fade-up"
              style={{ background: 'var(--nav-grad)', border: '1px solid rgba(255,255,255,0.1)' }}>
              {Object.values(PERSONAS).filter((u) => u.id !== persona).map((u) => (
                <button key={u.id} onClick={() => { setPersona(u.id); setOpen(false); }}
                  className="w-full flex items-center gap-2.5 p-3 text-left hover:bg-white/10 transition-all">
                  <div className={`w-7 h-7 rounded-full ${u.color} flex items-center justify-center text-white text-[10px] font-bold`}>
                    {u.avatar}
                  </div>
                  <div>
                    <p className="text-[11.5px] text-white/90 font-medium">{u.name}</p>
                    <p className="text-[9px] text-white/45">{u.sub}</p>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </nav>
  );
}

function DashSubnav({ tab, setTab }) {
  return (
    <div className="flex items-center gap-1.5 px-4 pt-3 relative z-[5]">
      {DASH_TABS.map((t) => (
        <button key={t.id} onClick={() => setTab(t.id)}
          className="px-3.5 py-1.5 rounded-full text-[11px] font-bold transition-all"
          style={tab === t.id
            ? { background: 'var(--brand)', color: 'white', boxShadow: '0 3px 10px rgba(26,115,232,0.3)' }
            : { background: 'var(--glass-strong)', color: 'var(--text-dim)', border: '1px solid var(--hairline)' }}>
          {t.label}
        </button>
      ))}
      <div className="accent-line ml-2" />
    </div>
  );
}

function Layout() {
  const [tab, setTab] = useState('landing');
  const isDash = DASH_IDS.includes(tab);

  const page = () => {
    switch (tab) {
      case 'landing': return <LandingPage go={setTab} />;
      case 'assistant': return <AssistantPage />;
      case 'overview': return <DashboardOverview />;
      case 'clinical': return <DashboardClinical />;
      case 'risk': return <DashboardRisk />;
      case 'cost': return <DashboardCost />;
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
      <TopNav tab={tab} setTab={setTab} />
      {isDash && <DashSubnav tab={tab} setTab={setTab} />}
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
