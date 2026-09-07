import { useEffect, useState } from 'react';
import { getDataRows, getDataTables } from '../services/api';
import { Spinner } from '../components/ui';

/** HIE browser — the relational exchange itself: 8 tables, longitudinal and coded. */
export default function DataPage() {
  const [tables, setTables] = useState(null);
  const [active, setActive] = useState('patient_summary');
  const [rows, setRows] = useState(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const limit = 40;

  useEffect(() => { getDataTables().then((r) => setTables(r.tables)).catch(() => setTables([])); }, []);
  useEffect(() => {
    setRows(null);
    getDataRows(active, offset, limit, search)
      .then((r) => { setRows(r.rows); setTotal(r.total); })
      .catch(() => setRows([]));
  }, [active, offset, search]);

  if (!tables) return <Spinner />;
  const activeMeta = tables.find((t) => t.name === active);
  const cols = rows?.length ? Object.keys(rows[0]) : (activeMeta?.columns || []);

  return (
    <div className="h-full flex gap-4 p-4">
      <div className="w-[250px] shrink-0 glass-card flex flex-col min-h-0">
        <div className="p-4 border-b border-[rgba(15,23,42,0.07)]">
          <p className="panel-title">HIE tables</p>
          <p className="text-[10px] mt-1.5 leading-snug" style={{ color: 'var(--text-dim)' }}>
            A real exchange shape: coded, longitudinal, relational. Phase 2 = FHIR R4 store → BigQuery streaming.
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {tables.map((t) => (
            <button key={t.name} onClick={() => { setActive(t.name); setOffset(0); setSearch(''); }}
              className="w-full text-left px-3 py-2 rounded-lg transition-all"
              style={t.name === active
                ? { background: 'rgba(26,115,232,0.12)', border: '1px solid rgba(26,115,232,0.30)', borderLeft: '3px solid var(--brand)' }
                : { border: '1px solid transparent' }}>
              <p className="text-[12px] font-bold" style={{ color: t.name === active ? 'var(--brand-lo)' : 'var(--text-md)' }}>
                {t.name}
              </p>
              <p className="text-[9.5px]" style={{ color: 'var(--text-faint)' }}>
                {t.rows.toLocaleString()} rows · {t.columns.length} cols
              </p>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 glass-card flex flex-col min-w-0 min-h-0">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[rgba(15,23,42,0.07)]">
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-bold" style={{ color: 'var(--text)' }}>{active}</p>
            <p className="text-[10px] truncate" style={{ color: 'var(--text-dim)' }}>{activeMeta?.description}</p>
          </div>
          <input value={search} onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
            placeholder="Search rows…"
            className="w-[180px] px-3 py-1.5 rounded-lg text-[11.5px] outline-none border"
            style={{ background: 'rgba(255,255,255,0.6)', borderColor: 'rgba(15,23,42,0.12)', color: 'var(--text)' }} />
          <div className="flex items-center gap-1.5 text-[10.5px]" style={{ color: 'var(--text-dim)' }}>
            <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}
              className="px-2 py-1 rounded disabled:opacity-30 hover:bg-[rgba(26,115,232,0.08)]">◀</button>
            {offset + 1}–{Math.min(offset + limit, total)} of {total.toLocaleString()}
            <button disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}
              className="px-2 py-1 rounded disabled:opacity-30 hover:bg-[rgba(26,115,232,0.08)]">▶</button>
          </div>
        </div>
        <div className="flex-1 overflow-auto">
          {rows === null ? <Spinner /> : (
            <table className="data-table">
              <thead>
                <tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    {cols.map((c) => (
                      <td key={c} className="max-w-[220px] overflow-hidden text-ellipsis">
                        {r[c] === null || r[c] === undefined ? '—' : String(r[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
