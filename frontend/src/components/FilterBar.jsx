import { useApp } from '../context/AppContext';

/**
 * The dashboard cross-filter, shown in every dashboard header. Chips come back from the
 * API (`filter.chips`), so the labels are the server's; the state lives in AppContext so a
 * filter chosen on the Registry tab still applies on Clinical Quality, Deterioration Risk
 * and Cost & Equity.
 */
export default function FilterBar({ info }) {
  const { dashFilter, toggleFilter, clearFilter } = useApp();
  const chips = info?.chips || [];
  const active = chips.length > 0 || Object.keys(dashFilter || {}).length > 0;
  return (
    <div className="filter-bar">
      {chips.map((c) => (
        <span key={c.key} className="filter-chip">
          <span className="k">{c.label}</span>
          <span>{c.value}</span>
          <button type="button" aria-label={`Remove ${c.label} filter`} onClick={() => toggleFilter(c.key, null)}>×</button>
        </span>
      ))}
      {active ? (
        <>
          {info && (
            <span className="filter-hint">
              <b style={{ color: 'var(--text-md)' }}>{info.patients.toLocaleString()}</b> of {info.total.toLocaleString()} patients
            </span>
          )}
          <button type="button" className="filter-clear" onClick={clearFilter}>Clear</button>
        </>
      ) : (
        <span className="filter-hint">Click a bar, slice or row to filter every panel</span>
      )}
    </div>
  );
}
