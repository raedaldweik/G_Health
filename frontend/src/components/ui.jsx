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
  nabd_supervisor: { bg: 'rgba(138,21,56,0.10)', fg: '#4a0c20', label: 'supervisor' },
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

/* ─── KPI strip — the reports hero-numbers recipe ─── */
const KPI_ICONS = {
  users: <><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></>,
  droplet: <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" />,
  check: <><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></>,
  heart: <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />,
  alert: <><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>,
  coins: <><circle cx="8" cy="8" r="6" /><path d="M18.09 10.37A6 6 0 1 1 10.34 18" /><path d="M7 6h1v4" /><path d="M16.71 13.88l.7.71-2.82 2.82" /></>,
  activity: <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />,
  gauge: <><path d="M12 2a10 10 0 1 0 10 10" /><path d="M12 12l6-6" /></>,
};

export function KpiStrip({ items }) {
  return (
    <div className="glass-card kpi-strip shrink-0"
      style={{ gridTemplateColumns: `repeat(${items.length}, 1fr)` }}>
      {items.map((k, i) => (
        <div key={i} className="kpi-strip-item">
          <div className={`kpi-strip-icon tone-${k.tone || 'teal'}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"
              strokeLinecap="round" strokeLinejoin="round">
              {KPI_ICONS[k.icon] || KPI_ICONS.activity}
            </svg>
          </div>
          <div className="kpi-strip-content">
            <div className="kpi-strip-top">
              <span className="kpi-strip-value">{k.value}{k.suffix && (
                <span style={{ fontSize: '0.55em', fontWeight: 700, color: 'var(--text-dim)', marginLeft: 2 }}>{k.suffix}</span>
              )}</span>
              {k.trend && (
                <span className={`kpi-strip-trend trend-${k.trendDir || 'flat'}`}>
                  {k.trendDir === 'up' ? '▲' : k.trendDir === 'down' ? '▼' : '•'} {k.trend}
                </span>
              )}
            </div>
            <span className="kpi-strip-label">{k.label}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
