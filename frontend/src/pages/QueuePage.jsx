import { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';
import { decideQueue, getQueue } from '../services/api';
import { Spinner } from '../components/ui';

const TYPE_ICONS = { prescription: '℞', recall_campaign: '📣', referral: '→', therapy_review: '⚕', prescription_draft: '℞' };

/** Human-in-the-loop queue: everything the agents draft waits here for a signature. */
export default function QueuePage() {
  const { personaInfo } = useApp();
  const [items, setItems] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = () => getQueue().then((r) => setItems(r.items)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  const decide = async (id, decision) => {
    setBusy(id);
    try {
      await decideQueue(id, decision, personaInfo.name);
      await load();
    } catch { /* leave list as-is */ }
    setBusy(null);
  };

  if (!items) return <Spinner />;
  const pending = items.filter((i) => i.status === 'pending');
  const resolved = items.filter((i) => i.status !== 'pending');

  const Card = ({ item, showActions }) => (
    <div className="glass-card p-4 animate-fade-up" style={{ overflow: 'visible' }}>
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center text-[15px] shrink-0"
          style={{ background: 'rgba(138,21,56,0.09)', color: 'var(--brand)' }}>
          {TYPE_ICONS[item.type] || '✎'}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[13px] font-bold" style={{ color: 'var(--text)' }}>{item.title}</span>
            <span className="badge badge-blue">{item.type.replace('_', ' ')}</span>
            {item.patient_id && <span className="text-[10.5px] font-mono" style={{ color: 'var(--text-dim)' }}>{item.patient_id}</span>}
            {item.patient_ids?.length > 1 && (
              <span className="text-[10.5px]" style={{ color: 'var(--text-dim)' }}>{item.patient_ids.length} patients</span>
            )}
            {item.status !== 'pending' && (
              <span className={`badge ${item.status === 'approved' ? 'badge-green' : 'badge-red'}`}>{item.status}</span>
            )}
          </div>
          <p className="text-[11.5px] mt-1 leading-relaxed" style={{ color: 'var(--text-md)' }}>{item.detail}</p>
          <div className="flex items-center gap-3 mt-1.5 text-[10px]" style={{ color: 'var(--text-faint)' }}>
            <span>drafted by <b>{item.drafted_by}</b></span>
            {item.citation && <span>📄 {item.citation}</span>}
            <span>{new Date(item.created_at).toLocaleString()}</span>
            {item.decided_by && <span>decided by {item.decided_by}</span>}
          </div>
        </div>
        {showActions && (
          <div className="flex gap-2 shrink-0">
            <button disabled={busy === item.id} onClick={() => decide(item.id, 'approved')}
              className="px-3.5 py-1.5 rounded-lg text-[11.5px] font-bold text-white transition-all hover:scale-[1.03] disabled:opacity-50"
              style={{ background: 'var(--green)' }}>
              Approve &amp; sign
            </button>
            <button disabled={busy === item.id} onClick={() => decide(item.id, 'rejected')}
              className="px-3.5 py-1.5 rounded-lg text-[11.5px] font-bold transition-all hover:scale-[1.03] disabled:opacity-50"
              style={{ background: 'var(--red-bg)', color: 'var(--red)', border: '1px solid rgba(185,28,44,0.25)' }}>
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="h-full overflow-y-auto p-5">
      <div className="max-w-[900px] mx-auto">
        <h1 className="text-[17px] font-extrabold tracking-tight" style={{ color: 'var(--text)' }}>
          Human-in-the-loop queue
        </h1>
        <p className="text-[11px] mt-1 mb-5" style={{ color: 'var(--text-dim)' }}>
          The agents draft; a clinician signs. <b>No clinical write ever happens without a human</b> —
          this queue is the safety model, and every decision lands in the audit trail.
        </p>

        <p className="panel-title mb-3">Awaiting approval · {pending.length}</p>
        <div className="space-y-3 mb-8">
          {pending.map((i) => <Card key={i.id} item={i} showActions />)}
          {pending.length === 0 && (
            <p className="text-[12px] py-6 text-center" style={{ color: 'var(--text-faint)' }}>
              Nothing pending — run a clinician scenario in the Assistant and the drafts appear here.
            </p>
          )}
        </div>

        {resolved.length > 0 && (
          <>
            <p className="panel-title mb-3">Decided · {resolved.length}</p>
            <div className="space-y-3 opacity-75">
              {resolved.slice(0, 12).map((i) => <Card key={i.id} item={i} showActions={false} />)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
