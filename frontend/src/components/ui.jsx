/** Shared glass UI primitives: KPI tile, dashboard panel, agent chip colors. */

export function KpiTile({ label, value, suffix, accent, sub }) {
  return (
    <div className="kpi-card" style={{ padding: '13px 16px' }}>
      <p className="text-[8.5px] font-bold tracking-[0.15em] uppercase mb-1" style={{ color: 'var(--text-faint)' }}>
        {label}
      </p>
      <p className="text-[21px] font-extrabold leading-none"
        style={{ color: accent === 'red' ? 'var(--red)' : 'var(--text)' }}>
        {value}
        {suffix && <span className="text-[12px] ml-0.5 font-bold" style={{ color: 'var(--text-dim)' }}>{suffix}</span>}
      </p>
      {sub && <p className="text-[9.5px] mt-1 font-semibold" style={{ color: 'var(--text-dim)' }}>{sub}</p>}
    </div>
  );
}

export function Panel({ title, right, children, className = '', pad = true }) {
  return (
    <div className={`glass-card flex flex-col h-full min-h-0 ${className}`}>
      <div className="flex items-center justify-between shrink-0 px-3.5 pt-2.5 pb-1.5">
        <h3 className="panel-title">{title}</h3>
        {right}
      </div>
      <div className={`flex-1 min-h-0 relative ${pad ? 'px-2 pb-2' : ''}`}>
        {children}
      </div>
    </div>
  );
}

export const AGENT_COLORS = {
  nabd_supervisor: { bg: 'rgba(26,115,232,0.10)', fg: '#0d366b', label: 'supervisor' },
  cohort_agent: { bg: 'rgba(42,120,214,0.12)', fg: '#1c5cab', label: 'cohort' },
  guideline_agent: { bg: 'rgba(0,131,0,0.10)', fg: '#006300', label: 'guidelines' },
  risk_agent: { bg: 'rgba(235,104,52,0.12)', fg: '#9a3b12', label: 'risk · ML' },
  pophealth_agent: { bg: 'rgba(74,58,167,0.12)', fg: '#4a3aa7', label: 'pop-health MCP' },
  action_agent: { bg: 'rgba(180,83,9,0.12)', fg: '#b45309', label: 'actions' },
  system: { bg: 'rgba(100,116,139,0.12)', fg: '#475569', label: 'system' },
};

export function AgentChip({ agent }) {
  const c = AGENT_COLORS[agent] || AGENT_COLORS.system;
  return (
    <span className="agent-chip" style={{ background: c.bg, color: c.fg }}>
      {c.label}
    </span>
  );
}

export function Spinner() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="w-6 h-6 rounded-full border-2 border-transparent animate-spin"
        style={{ borderTopColor: 'var(--brand)' }} />
    </div>
  );
}
