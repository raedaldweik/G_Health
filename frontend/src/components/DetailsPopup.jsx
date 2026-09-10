import { AgentChip } from './ui';

const STATUS = {
  pass:      { mark: '✓', color: 'var(--green)', bg: 'var(--green-bg)' },
  attention: { mark: '!', color: 'var(--amber)', bg: 'var(--amber-bg)' },
  info:      { mark: '·', color: 'var(--text-dim)', bg: 'rgba(15,23,42,0.06)' },
};

function Section({ title, children }) {
  return (
    <div>
      <p className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--text-dim)' }}>
        {title}
      </p>
      {children}
    </div>
  );
}

/** The governance record for one answer: the enforced controls, data access,
 *  model accounting, every agent hop, the cited sources and the audit entries
 *  this turn persisted — the "nothing is a black box" view. */
export default function DetailsPopup({ data, query, onClose, onOpenSource }) {
  if (!data) return null;
  const usage = data.usage || {};
  const g = data.governance;
  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-6" onClick={onClose}
      style={{ background: 'rgba(10,22,40,0.45)', backdropFilter: 'blur(4px)' }}>
      <div className="glass-card w-full max-w-[760px] max-h-[85vh] flex flex-col animate-slide-up"
        onClick={(e) => e.stopPropagation()} style={{ background: 'rgba(255,255,255,0.96)' }}>

        <div className="flex items-center justify-between px-5 py-3 border-b border-[rgba(138,21,56,0.10)]">
          <div className="flex items-center gap-2">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span className="text-sm font-bold" style={{ color: 'var(--text)' }}>Governance record</span>
            {g?.summary && (
              <span className={`badge ${g.summary.attention > 0 ? 'badge-amber' : 'badge-green'}`}>
                {g.summary.attention > 0
                  ? `${g.summary.attention} of ${g.summary.controls} controls need attention`
                  : `${g.summary.controls} controls enforced`}
              </span>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[rgba(138,21,56,0.08)]" style={{ color: 'var(--text-dim)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <div className="rounded-xl px-4 py-3" style={{ background: 'rgba(138,21,56,0.05)', border: '1px solid rgba(138,21,56,0.14)' }}>
            <p className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--text-dim)' }}>Question</p>
            <p className="text-[12.5px] leading-relaxed" style={{ color: 'var(--text)' }}>{query || '(unknown)'}</p>
          </div>

          {/* Controls */}
          {g?.checks?.length > 0 && (
            <Section title="Controls in force for this answer">
              <div className="space-y-1.5">
                {g.checks.map((c) => {
                  const s = STATUS[c.status] || STATUS.info;
                  return (
                    <div key={c.id} className="flex items-start gap-2.5 rounded-lg px-3 py-2"
                      style={{ border: '1px solid rgba(138,21,56,0.10)' }}>
                      <span className="shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-extrabold mt-[1px]"
                        style={{ background: s.bg, color: s.color }}>{s.mark}</span>
                      <div className="min-w-0">
                        <p className="text-[11.5px] font-bold" style={{ color: 'var(--text)' }}>{c.label}</p>
                        <p className="text-[11px] leading-snug mt-0.5" style={{ color: 'var(--text-md)' }}>{c.detail}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </Section>
          )}

          {/* Model & usage */}
          <Section title="Model & usage accounting">
            <div className="flex flex-wrap gap-2">
              {data.model && <span className="badge badge-blue">{data.model}</span>}
              {usage?.total_tokens != null && (
                <>
                  <span className="badge badge-blue">{usage.total_tokens.toLocaleString()} tokens</span>
                  <span className="badge badge-blue">{usage.prompt_tokens?.toLocaleString()} prompt / {usage.completion_tokens?.toLocaleString()} completion</span>
                  <span className="badge badge-blue">{usage.llm_calls} LLM calls</span>
                  {usage.wall_ms != null && <span className="badge badge-blue">{(usage.wall_ms / 1000).toFixed(1)} s wall · first token {usage.first_token_ms != null ? `${(usage.first_token_ms / 1000).toFixed(1)} s` : 'n/a'}</span>}
                  {usage.thinking_level && <span className="badge badge-blue">thinking {usage.thinking_level.toLowerCase()}</span>}
                </>
              )}
              <span className="badge badge-blue">{(data.trace || []).length} tool steps</span>
              {g?.model?.switches > 0 && <span className="badge badge-amber">{g.model.switches} capacity fallback(s)</span>}
            </div>
          </Section>

          {/* Data access */}
          {g?.data_access && (
            <Section title="Data access">
              <div className="flex flex-wrap gap-2 items-center">
                <span className="badge badge-green">read-only data plane</span>
                {(g.data_access.patients || []).length > 0
                  ? g.data_access.patients.map((p) => <span key={p} className="badge badge-blue">patient {p}</span>)
                  : <span className="badge badge-blue">population aggregates only</span>}
                {(g.data_access.agents || []).map((a) => <AgentChip key={a} agent={a} />)}
              </div>
            </Section>
          )}

          {/* Tool calls */}
          <Section title="Tool calls: every agent hop">
            <div className="space-y-2">
              {(data.trace || []).map((t, i) => (
                <div key={i} className="rounded-lg px-3 py-2.5" style={{ border: '1px solid rgba(138,21,56,0.10)' }}>
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
                      style={{ background: 'rgba(138,21,56,0.12)', color: 'var(--brand)' }}>{i + 1}</span>
                    <AgentChip agent={t.agent} />
                    <span className="text-[12px] font-bold font-mono" style={{ color: 'var(--brand-lo)' }}>{t.tool}</span>
                    {t.duration_ms != null && <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>{t.duration_ms} ms</span>}
                  </div>
                  {t.args_summary && (
                    <pre className="text-[10.5px] px-2.5 py-1.5 rounded-lg whitespace-pre-wrap break-all font-mono mb-1"
                      style={{ background: 'rgba(15,23,42,0.035)', color: 'var(--text-md)' }}>
                      in: {t.args_summary}
                    </pre>
                  )}
                  {t.result_summary && (
                    <pre className="text-[10.5px] px-2.5 py-1.5 rounded-lg whitespace-pre-wrap break-all font-mono"
                      style={{ background: 'rgba(15,23,42,0.035)', color: 'var(--text-md)' }}>
                      out: {t.result_summary}
                    </pre>
                  )}
                </div>
              ))}
              {(data.trace || []).length === 0 && (
                <p className="text-[11.5px]" style={{ color: 'var(--text-dim)' }}>No tool calls recorded for this answer.</p>
              )}
            </div>
          </Section>

          {/* Sources */}
          {data.citations?.length > 0 && (
            <Section title="Retrieved guideline passages">
              <div className="space-y-2">
                {data.citations.map((c, i) => (
                  <div key={i} className="rounded-lg px-3 py-2.5" style={{ border: '1px solid rgba(138,21,56,0.10)' }}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[11.5px] font-bold truncate" style={{ color: 'var(--brand-lo)' }}>{c.doc}</span>
                      <span className="badge badge-blue">p. {c.page}</span>
                      {onOpenSource && (
                        <button onClick={() => onOpenSource(c)} className="text-[10.5px] font-semibold hover:underline ml-auto shrink-0"
                          style={{ color: 'var(--brand)' }}>open ↗</button>
                      )}
                    </div>
                    <p className="text-[11.5px] leading-[1.7] max-h-[110px] overflow-y-auto" style={{ color: 'var(--text-md)' }}>
                      {c.snippet}
                    </p>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Audit entries */}
          {g?.audit?.events?.length > 0 && (
            <Section title={`Audit trail entries persisted this turn (${g.audit.count})`}>
              <div className="space-y-1">
                {g.audit.events.map((e) => (
                  <div key={e.id} className="flex items-center gap-2 rounded-lg px-3 py-1.5 min-w-0"
                    style={{ border: '1px solid rgba(138,21,56,0.08)' }}>
                    <span className={`badge shrink-0 ${e.severity === 'warning' ? 'badge-amber' : e.severity === 'action' ? 'badge-blue' : 'badge-green'}`}>
                      {e.event_type}
                    </span>
                    <span className="text-[10.5px] truncate flex-1" style={{ color: 'var(--text-md)' }}>{e.detail}</span>
                    <span className="text-[9.5px] font-mono shrink-0" style={{ color: 'var(--text-faint)' }}>{e.id}</span>
                  </div>
                ))}
              </div>
              <p className="text-[10px] mt-1.5" style={{ color: 'var(--text-faint)' }}>
                Entries are persisted server-side and reviewable on the Audit tab.
              </p>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}
