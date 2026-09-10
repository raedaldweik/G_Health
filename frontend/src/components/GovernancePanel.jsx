import { useState } from 'react';
import { AgentChip } from './ui';
import ToolTrace from './ToolTrace';

const STATUS = {
  pass:      { mark: '✓', color: 'var(--green)', bg: 'var(--green-bg)' },
  attention: { mark: '!', color: 'var(--amber)', bg: 'var(--amber-bg)' },
  info:      { mark: '·', color: 'var(--text-dim)', bg: 'rgba(15,23,42,0.06)' },
};

function StatusDot({ status }) {
  const s = STATUS[status] || STATUS.info;
  return (
    <span className="shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-extrabold mt-[1px]"
      style={{ background: s.bg, color: s.color }}>{s.mark}</span>
  );
}

/** Per-answer governance panel: the controls that were in force while this answer
 *  was produced (grounding, consent, human oversight, data boundary, model
 *  transparency, audit linkage), with the execution trace nested inside.
 *  Falls back to the plain trace for answers without a governance record. */
export default function GovernancePanel({ data }) {
  const [open, setOpen] = useState(false);
  const g = data?.governance;
  if (!g) return <ToolTrace trace={data?.trace} />;

  const trace = data.trace || [];
  const attention = g.summary?.attention || 0;
  const headline = attention > 0
    ? `${g.summary.controls} controls · ${attention} need${attention === 1 ? 's' : ''} attention`
    : `${g.summary?.controls ?? g.checks.length} controls enforced`;

  return (
    <div className="trace-panel mt-2">
      <div className="trace-header" onClick={() => setOpen(!open)}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
          stroke={attention > 0 ? 'var(--amber)' : 'var(--green)'} strokeWidth="2.5">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        <span>Governance · {headline} · {g.audit?.count ?? 0} audit event{(g.audit?.count ?? 0) !== 1 ? 's' : ''}</span>
        <div className="flex-1" />
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>

      {open && (
        <div className="animate-slide-up px-3 pb-3">
          {/* Controls */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 pt-2.5">
            {g.checks.map((c) => (
              <div key={c.id} className="flex items-start gap-2 min-w-0">
                <StatusDot status={c.status} />
                <div className="min-w-0">
                  <p className="text-[11px] font-bold leading-tight" style={{ color: 'var(--text)' }}>{c.label}</p>
                  <p className="text-[10px] leading-snug mt-0.5" style={{ color: 'var(--text-dim)' }}>{c.detail}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Data access line */}
          {(g.data_access?.patients?.length > 0 || g.data_access?.tools?.length > 0) && (
            <div className="mt-3 pt-2.5 border-t border-[rgba(15,23,42,0.07)] flex flex-wrap items-center gap-1.5">
              <span className="text-[9.5px] font-bold uppercase tracking-wider mr-1" style={{ color: 'var(--text-faint)' }}>
                Data access
              </span>
              <span className="badge badge-green">read-only</span>
              {g.data_access.patients.map((p) => <span key={p} className="badge badge-blue">{p}</span>)}
              {g.data_access.patients.length === 0 && <span className="badge badge-blue">aggregates only</span>}
            </div>
          )}

          {/* Execution trace */}
          {trace.length > 0 && (
            <div className="mt-3 pt-2.5 border-t border-[rgba(15,23,42,0.07)]">
              <p className="text-[9.5px] font-bold uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-faint)' }}>
                Execution trace · {trace.length} step{trace.length !== 1 ? 's' : ''}
              </p>
              {trace.map((t, i) => (
                <div key={i} className="flex items-center gap-2 py-[3px] min-w-0">
                  <span className="text-[9.5px] w-4 text-right shrink-0" style={{ color: 'var(--text-faint)' }}>{i + 1}</span>
                  <AgentChip agent={t.agent} />
                  <span className="trace-step-tool truncate">{t.tool}</span>
                  <span className="text-[10px] truncate flex-1" style={{ color: 'var(--text-dim)' }}>{t.result_summary}</span>
                  {t.duration_ms != null && (
                    <span className="text-[9.5px] shrink-0" style={{ color: 'var(--text-faint)' }}>{t.duration_ms} ms</span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Audit linkage */}
          {g.audit?.count > 0 && (
            <div className="mt-3 pt-2.5 border-t border-[rgba(15,23,42,0.07)] flex flex-wrap items-center gap-1.5">
              <span className="text-[9.5px] font-bold uppercase tracking-wider mr-1" style={{ color: 'var(--text-faint)' }}>
                Audit trail
              </span>
              {g.audit.events.slice(0, 6).map((e) => (
                <span key={e.id} className={`badge ${e.severity === 'warning' ? 'badge-amber' : e.severity === 'action' ? 'badge-blue' : 'badge-green'}`}
                  title={e.detail}>{e.event_type}</span>
              ))}
              {g.audit.count > 6 && <span className="badge badge-blue">+{g.audit.count - 6}</span>}
              <span className="text-[9.5px]" style={{ color: 'var(--text-faint)' }}>
                persisted · full trail in the Audit tab
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
