import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DynamicChart from './DynamicChart';
import ToolTrace from './ToolTrace';
import { AgentChip } from './ui';

const md = {
  p: (p) => <p className="my-1 leading-[1.75]" {...p} />,
  strong: (p) => <strong style={{ color: 'var(--brand)', fontWeight: 700 }} {...p} />,
  em: (p) => <em style={{ color: 'var(--brand-lo)' }} {...p} />,
  ul: (p) => <ul className="my-1.5 space-y-0.5 pl-5 list-disc" {...p} />,
  ol: (p) => <ol className="my-1.5 space-y-0.5 pl-5 list-decimal" {...p} />,
  li: (p) => <li className="leading-[1.7]" {...p} />,
  h1: (p) => <h1 className="text-[15px] font-bold my-2" style={{ color: 'var(--brand)' }} {...p} />,
  h2: (p) => <h2 className="text-[14px] font-bold my-2" style={{ color: 'var(--brand)' }} {...p} />,
  h3: (p) => <h3 className="text-[13px] font-semibold my-1.5" style={{ color: 'var(--brand-lo)' }} {...p} />,
  table: (p) => (
    <div className="my-2 overflow-x-auto">
      <table className="border-collapse text-[12px] w-full" style={{ border: '1px solid rgba(26,115,232,0.15)' }} {...p} />
    </div>
  ),
  thead: (p) => <thead style={{ background: 'rgba(26,115,232,0.06)' }} {...p} />,
  th: (p) => <th className="px-2 py-1.5 text-left font-semibold" style={{ border: '1px solid rgba(26,115,232,0.15)', color: 'var(--brand)' }} {...p} />,
  td: (p) => <td className="px-2 py-1.5" style={{ border: '1px solid rgba(26,115,232,0.10)' }} {...p} />,
  code: (p) => <code className="px-1 py-0.5 rounded text-[12px]" style={{ background: 'rgba(26,115,232,0.08)', color: 'var(--brand)' }} {...p} />,
  pre: (p) => <pre className="p-2 rounded my-1 text-[12px] overflow-x-auto" style={{ background: 'rgba(0,0,0,0.04)' }} {...p} />,
  blockquote: (p) => <blockquote className="pl-3 my-2 italic" style={{ borderLeft: '2px solid var(--brand-lo)', color: 'var(--text-md)' }} {...p} />,
};

/** One completed assistant answer: markdown, charts, citations, drafted actions,
 *  collapsible tool trace, usage footer + details view. */
export default function ResponseCard({ data, onOpenSource, onOpenDetails }) {
  if (!data) return null;
  const usage = data.usage;
  const citations = [];
  const seen = new Set();
  for (const c of data.citations || []) {
    const k = `${c.doc}|${c.page}`;
    if (!seen.has(k)) { seen.add(k); citations.push(c); }
  }
  return (
    <div className="animate-slide-up space-y-2.5 max-w-[680px]">
      <div className="msg-bot-bubble px-4 py-3">
        <div className="text-[13px]" style={{ color: 'var(--text)' }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={md}>
            {data.answer || '_(empty answer)_'}
          </ReactMarkdown>
        </div>
      </div>

      {(data.charts || []).map((spec, i) => <DynamicChart key={i} spec={spec} />)}

      {/* Guideline citations — click to read the passage */}
      {citations.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {citations.map((c, i) => (
            <button key={i} onClick={() => onOpenSource?.(c)}
              title="Open the cited guideline passage"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] transition-all cursor-pointer hover:shadow-md hover:-translate-y-[1px]"
              style={{ color: 'var(--brand-lo)', background: 'rgba(26,115,232,0.06)', border: '1px solid rgba(26,115,232,0.18)' }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
              </svg>
              {c.doc} · p.{c.page}
            </button>
          ))}
        </div>
      )}

      {/* Drafted actions → HITL queue */}
      {data.actions?.length > 0 && (
        <div className="space-y-1.5">
          {data.actions.map((a, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11.5px]"
              style={{ background: 'var(--amber-bg)', border: '1px solid rgba(180,83,9,0.25)', color: 'var(--amber)' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <span className="font-bold">Draft {a.draft_id}</span>
              <span>queued — awaiting human approval in the Queue tab. No EMR write has occurred.</span>
            </div>
          ))}
        </div>
      )}

      <ToolTrace trace={data.trace} />

      <div className="flex items-center gap-3 px-1 text-[10px]" style={{ color: 'var(--text-faint)' }}>
        {onOpenDetails && (
          <button onClick={() => onOpenDetails(data)} title="Full trace: every agent hop, tool call and token count"
            className="p-1 rounded-md transition-all hover:bg-[rgba(26,115,232,0.10)]" style={{ color: 'var(--text-dim)' }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
          </button>
        )}
        {data.model && <span>{data.model}</span>}
        {usage?.total_tokens != null && (
          <span>{usage.total_tokens.toLocaleString()} tokens · {usage.llm_calls} LLM calls</span>
        )}
        {data.trace?.length > 0 && <span>{data.trace.length} tool steps</span>}
      </div>
    </div>
  );
}

export { AgentChip };
