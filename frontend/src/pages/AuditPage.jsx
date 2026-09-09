import { useEffect, useState } from 'react';
import { getAudit } from '../services/api';
import { Spinner } from '../components/ui';

const EVENT_STYLE = {
  'CONSENT·DENY': { color: 'var(--red)', bg: 'var(--red-bg)' },
  'HITL·DRAFT': { color: 'var(--amber)', bg: 'var(--amber-bg)' },
  'HITL·APPROVED': { color: 'var(--green)', bg: 'var(--green-bg)' },
  'HITL·REJECTED': { color: 'var(--red)', bg: 'var(--red-bg)' },
  'ML·SCORE': { color: '#9a3b12', bg: 'rgba(235,104,52,0.10)' },
  'ML·SIMULATE': { color: '#9a3b12', bg: 'rgba(235,104,52,0.10)' },
  'MCP·DRAFT': { color: '#4a3aa7', bg: 'rgba(74,58,167,0.10)' },
  'RAG·SEARCH': { color: '#006300', bg: 'rgba(0,131,0,0.08)' },
  'FHIR·READ': { color: '#1c5cab', bg: 'rgba(42,120,214,0.10)' },
};

/** Governance trail: every tool call, consent denial, model score and human decision. */
export default function AuditPage() {
  const [entries, setEntries] = useState(null);
  useEffect(() => {
    getAudit().then((r) => setEntries(r.entries)).catch(() => setEntries([]));
  }, []);
  if (!entries) return <Spinner />;

  return (
    <div className="h-full overflow-y-auto p-5">
      <div className="max-w-[900px] mx-auto">
        <h1 className="text-[17px] font-extrabold tracking-tight" style={{ color: 'var(--text)' }}>
          Audit trail
        </h1>
        <p className="text-[11px] mt-1 mb-5" style={{ color: 'var(--text-dim)' }}>
          Every agent tool call, guideline retrieval, model score, consent denial and human decision: 
          logged. Phase 2 maps this to Cloud Audit Logs + OpenTelemetry tracing on Agent Engine.
        </p>

        <div className="glass-card">
          {entries.map((e, i) => {
            const st = EVENT_STYLE[e.event_type] || { color: 'var(--text-dim)', bg: 'rgba(15,23,42,0.04)' };
            return (
              <div key={e.id} className={`flex items-start gap-3 px-4 py-2.5 ${i !== entries.length - 1 ? 'border-b border-[rgba(15,23,42,0.05)]' : ''}`}>
                <span className="text-[9.5px] font-bold px-2 py-1 rounded-md shrink-0 mt-0.5 whitespace-nowrap"
                  style={{ color: st.color, background: st.bg }}>
                  {e.event_type}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-[11.5px] leading-relaxed" style={{ color: 'var(--text-md)' }}>{e.detail}</p>
                  <p className="text-[9.5px] mt-0.5" style={{ color: 'var(--text-faint)' }}>
                    {e.actor} · {new Date(e.timestamp).toLocaleString()}
                    {e.patient_id && <> · <span className="font-mono">{e.patient_id}</span></>}
                  </p>
                </div>
              </div>
            );
          })}
          {entries.length === 0 && (
            <p className="text-[12px] py-8 text-center" style={{ color: 'var(--text-faint)' }}>
              No audit entries yet. Interact with the Assistant and this trail fills up.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
