import { AgentChip } from './ui';

/** Full traceability popup: the question, per-agent tool calls with args/results,
 *  citations, drafted actions and token usage — the "nothing is a black box" view. */
export default function DetailsPopup({ data, query, onClose, onOpenSource }) {
  if (!data) return null;
  const usage = data.usage || {};
  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-6" onClick={onClose}
      style={{ background: 'rgba(10,22,40,0.45)', backdropFilter: 'blur(4px)' }}>
      <div className="glass-card w-full max-w-[760px] max-h-[85vh] flex flex-col animate-slide-up"
        onClick={(e) => e.stopPropagation()} style={{ background: 'rgba(255,255,255,0.96)' }}>

        <div className="flex items-center justify-between px-5 py-3 border-b border-[rgba(26,115,232,0.10)]">
          <div className="flex items-center gap-2">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
            <span className="text-sm font-bold" style={{ color: 'var(--text)' }}>Full trace</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[rgba(26,115,232,0.08)]" style={{ color: 'var(--text-dim)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          <div className="rounded-xl px-4 py-3" style={{ background: 'rgba(26,115,232,0.05)', border: '1px solid rgba(26,115,232,0.14)' }}>
            <p className="text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: 'var(--text-dim)' }}>Question</p>
            <p className="text-[12.5px] leading-relaxed" style={{ color: 'var(--text)' }}>{query || '(unknown)'}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            {data.model && <span className="badge badge-blue">{data.model}</span>}
            {usage?.total_tokens != null && (
              <>
                <span className="badge badge-blue">{usage.total_tokens.toLocaleString()} tokens</span>
                <span className="badge badge-blue">{usage.prompt_tokens?.toLocaleString()} prompt / {usage.completion_tokens?.toLocaleString()} completion</span>
                <span className="badge badge-blue">{usage.llm_calls} LLM calls</span>
              </>
            )}
            <span className="badge badge-blue">{(data.trace || []).length} tool steps</span>
          </div>

          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--text-dim)' }}>
              Tool calls — every agent hop
            </p>
            <div className="space-y-2">
              {(data.trace || []).map((t, i) => (
                <div key={i} className="rounded-lg px-3 py-2.5" style={{ border: '1px solid rgba(26,115,232,0.10)' }}>
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
                      style={{ background: 'rgba(26,115,232,0.12)', color: 'var(--brand)' }}>{i + 1}</span>
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
          </div>

          {data.citations?.length > 0 && (
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider mb-2" style={{ color: 'var(--text-dim)' }}>
                Retrieved guideline passages
              </p>
              <div className="space-y-2">
                {data.citations.map((c, i) => (
                  <div key={i} className="rounded-lg px-3 py-2.5" style={{ border: '1px solid rgba(26,115,232,0.10)' }}>
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
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
