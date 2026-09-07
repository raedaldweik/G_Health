import { useState } from 'react';
import { AgentChip } from './ui';

/** Collapsible per-answer trace of every agent hop + tool call. */
export default function ToolTrace({ trace }) {
  const [open, setOpen] = useState(false);
  if (!trace || trace.length === 0) return null;
  const agents = [...new Set(trace.map((t) => t.agent))];

  return (
    <div className="trace-panel mt-2">
      <div className="trace-header" onClick={() => setOpen(!open)}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" />
        </svg>
        <span>Agent trace · {trace.length} step{trace.length !== 1 ? 's' : ''} · {agents.length} agent{agents.length !== 1 ? 's' : ''}</span>
        <div className="flex-1" />
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
          style={{ transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>
      {open && (
        <div className="animate-slide-up">
          {trace.map((t, i) => (
            <div key={i} className="trace-step">
              <div className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold mt-0.5"
                style={{ background: 'rgba(138,100,32,0.15)', color: 'var(--teal)' }}>
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-0.5">
                  <AgentChip agent={t.agent} />
                  <span className="trace-step-tool">{t.tool}</span>
                  {t.duration_ms != null && (
                    <span className="text-[9.5px]" style={{ color: 'var(--text-faint)' }}>{t.duration_ms} ms</span>
                  )}
                </div>
                {t.args_summary && (
                  <div className="text-[10.5px] font-mono break-all" style={{ color: 'var(--text-dim)' }}>
                    → {t.args_summary}
                  </div>
                )}
                {t.result_summary && (
                  <div className="text-[10.5px] break-all" style={{ color: 'var(--text-md)' }}>
                    ✓ {t.result_summary}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
