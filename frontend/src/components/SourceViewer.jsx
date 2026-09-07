/** Modal showing a cited guideline passage, with a link to the source PDF page. */
export default function SourceViewer({ source, onClose }) {
  if (!source) return null;
  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center p-6" onClick={onClose}
      style={{ background: 'rgba(10,22,40,0.45)', backdropFilter: 'blur(4px)' }}>
      <div className="glass-card w-full max-w-[560px] max-h-[75vh] flex flex-col animate-slide-up"
        onClick={(e) => e.stopPropagation()} style={{ background: 'rgba(255,255,255,0.96)' }}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-[rgba(138,21,56,0.10)]">
          <div className="min-w-0">
            <p className="text-sm font-bold truncate" style={{ color: 'var(--text)' }}>{source.doc}</p>
            <p className="text-[10.5px]" style={{ color: 'var(--text-dim)' }}>Retrieved passage · page {source.page}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[rgba(138,21,56,0.08)]" style={{ color: 'var(--text-dim)' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <p className="text-[12.5px] leading-[1.8] whitespace-pre-wrap" style={{ color: 'var(--text-md)' }}>
            {source.snippet || '(no text)'}
          </p>
        </div>
        {source.file && (
          <div className="px-5 py-3 border-t border-[rgba(138,21,56,0.10)]">
            <a href={`/api/documents/file/${source.file}#page=${source.page}`} target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-[11.5px] font-bold hover:underline"
              style={{ color: 'var(--brand)' }}>
              Open source PDF at page {source.page} ↗
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
