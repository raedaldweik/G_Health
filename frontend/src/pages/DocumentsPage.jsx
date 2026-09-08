import { useEffect, useState } from 'react';
import { getDocuments } from '../services/api';
import { Spinner } from '../components/ui';

/** The RAG corpus: national clinical guidelines the agent grounds every claim in. */
export default function DocumentsPage() {
  const [d, setD] = useState(null);
  useEffect(() => {
    let timer;
    const tick = () => getDocuments().then((r) => {
      setD(r);
      if (r?.status?.semantic_index === 'building') timer = setTimeout(tick, 3000);
    }).catch(() => setD({ documents: [], status: {} }));
    tick();
    return () => clearTimeout(timer);
  }, []);
  if (!d) return <Spinner />;

  return (
    <div className="h-full overflow-y-auto p-5">
      <div className="max-w-[980px] mx-auto">
        <div className="flex items-end justify-between mb-1">
          <h1 className="text-[17px] font-extrabold tracking-tight" style={{ color: 'var(--text)' }}>
            Guideline corpus
          </h1>
          <span className="status-pill" title={d.status.error || undefined}>
            <span className={`w-2 h-2 rounded-full ${d.status.semantic_index === 'building' ? 'animate-pulse' : ''}`}
              style={{ background: d.status.semantic_index === 'ready' ? 'var(--green)'
                : d.status.semantic_index === 'building' ? 'var(--amber)' : 'var(--red)' }} />
            {d.status.chunks} chunks · retrieval: {d.status.semantic_index === 'ready'
              ? `hybrid — BM25 + ${d.status.embed_model} (${d.status.vectors} vectors × ${d.status.dims} dims)`
              : d.status.semantic_index === 'building' ? `BM25 now · embedding ${d.status.chunks} chunks with ${d.status.embed_model}…`
              : d.status.semantic_index === 'failed' ? `BM25 only — embeddings failed: ${d.status.error}`
              : 'BM25 keyword only (no Gemini key)'}
          </span>
        </div>
        <p className="text-[11px] mb-5" style={{ color: 'var(--text-dim)' }}>
          The agent never answers clinical questions from memory — it retrieves from these documents at
          query time and cites document + page. Drop a new PDF in and it's indexed on restart, no retraining.
          Phase 2: this layer becomes Vertex AI RAG Engine (managed corpus, gemini-embedding-001).
        </p>

        <div className="grid grid-cols-2 gap-3">
          {d.documents.map((doc) => (
            <a key={doc.file} href={`/api/documents/file/${doc.file}`} target="_blank" rel="noreferrer"
              className="glass-card p-4 flex items-start gap-3 transition-all hover:-translate-y-[2px]">
              <div className="w-10 h-12 rounded-md flex items-center justify-center shrink-0"
                style={{ background: 'rgba(185,28,44,0.08)', border: '1px solid rgba(185,28,44,0.15)' }}>
                <span className="text-[9px] font-extrabold" style={{ color: 'var(--red)' }}>PDF</span>
              </div>
              <div className="min-w-0">
                <p className="text-[12.5px] font-bold leading-snug" style={{ color: 'var(--text)' }}>{doc.doc}</p>
                <p className="text-[10.5px] mt-1" style={{ color: 'var(--text-dim)' }}>
                  {doc.pages} pages · {doc.chunks} chunks · {doc.size_mb} MB
                </p>
              </div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
