import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine,
} from 'recharts';
import { Bar3D, Donut3D } from './Chart3D';
import MapCard from './MapCard';

/*
 * DynamicChart, renders a chart spec (from the agent's render_chart tool or a
 * dashboard endpoint) with the validated categorical palette and the dataviz
 * mark specs: thin rounded bars, 2px lines, recessive grid, glass tooltip,
 * legend only when ≥2 series.
 *
 * spec: { type: bar|line|area|pie|scatter, title, subtitle, data:[{...}],
 *         xKey, yKeys:[{key,label,color}], stacked, yAxisLabel, footnote,
 *         referenceY }
 */

// Validated categorical palette, the reports ramp mid-tones, fixed order.
export const PALETTE = ['#9b1c46', '#b8862e', '#6d4fa8', '#3a8e5a', '#d97706', '#a8407a'];

const AXIS_TICK = { fontSize: 10, fill: '#64748b', fontFamily: 'Manrope' };
const GRID = 'rgba(15,23,42,0.07)';

function GlassTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <div className="tip-label">{label}</div>
      {payload.filter((p) => p.value != null).map((p, i) => (
        <div key={i} className="tip-row">
          <span className="tip-dot" style={{ background: p.color || p.fill }} />
          <span style={{ color: 'var(--text-md)' }}>{p.name}</span>
          <span className="tip-val">
            {typeof p.value === 'number' ? p.value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

const legendStyle = { fontSize: 10.5, fontFamily: 'Manrope' };

export default function DynamicChart({ spec, bare = false, height = 230, onSelect, activeLabel = null }) {
  if (spec?.type === 'map') return <MapCard spec={spec} height={bare ? '100%' : 360} compact={bare} />;
  if (!spec || !Array.isArray(spec.data) || spec.data.length === 0) return null;
  const type = (spec.type || 'bar').toLowerCase();
  const yKeys = (spec.yKeys || []).filter(Boolean).map((k, i) => ({
    key: k.key, label: k.label || k.key, color: k.color || PALETTE[i % PALETTE.length],
  }));
  if (!yKeys.length) return null;
  const multi = yKeys.length > 1;
  const data = spec.data.slice(0, 60);
  const rotate = data.length > 7 || data.some((d) => String(d[spec.xKey] ?? '').length > 8);

  const xAxis = (
    <XAxis dataKey={spec.xKey} tick={{ ...AXIS_TICK, ...(rotate ? { angle: -32, textAnchor: 'end' } : {}) }}
      height={rotate ? 58 : 24} interval={data.length > 24 ? Math.floor(data.length / 12) : 0}
      tickLine={false} axisLine={{ stroke: 'rgba(15,23,42,0.15)' }} />
  );
  const yAxis = (
    <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} width={44}
      label={spec.yAxisLabel ? {
        value: spec.yAxisLabel, angle: -90, position: 'insideLeft',
        style: { fontSize: 10, fill: '#94a3b8' },
      } : undefined}
      domain={type === 'line' || type === 'area' ? ['auto', 'auto'] : [0, 'auto']} />
  );
  const grid = <CartesianGrid stroke={GRID} vertical={false} />;
  const tip = <Tooltip content={<GlassTooltip />} cursor={{ fill: 'rgba(138,21,56,0.05)' }} />;
  const legend = multi ? <Legend wrapperStyle={legendStyle} iconSize={9} /> : null;
  const refLine = spec.referenceY != null ? (
    <ReferenceLine y={spec.referenceY} stroke="#94a3b8" strokeDasharray="4 3"
      label={{ value: spec.referenceLabel || 'target', fontSize: 9.5, fill: '#64748b', position: 'right' }} />
  ) : null;

  // Single-series bar → the signature reports 3D bar; pie → the 3D donut.
  const to3dRows = (k) => data.map((r) => ({ label: String(r[spec.xKey] ?? ''), value: Number(r[k.key]) }))
    .filter((r) => isFinite(r.value));
  const wrap3d = (inner, minH) => bare
    ? <div style={{ width: '100%', height: '100%' }}>{inner}</div>
    : (
      <div className="mt-2 max-w-full animate-fade-up">
        <div className="text-[12.5px] font-bold mb-0.5" style={{ color: 'var(--brand)' }}>{spec.title || 'Chart'}</div>
        {spec.subtitle && <div className="text-[11px] mb-1.5" style={{ color: 'var(--text-dim)' }}>{spec.subtitle}</div>}
        <div className="rounded-xl px-2 pt-2 pb-1" style={{
          background: 'var(--glass-strong)', border: '1px solid var(--glass-border)',
          boxShadow: 'var(--glass-shadow)', backdropFilter: 'blur(14px)', height: minH,
        }}>
          {inner}
        </div>
        {spec.footnote && <div className="text-[10px] mt-1 px-1" style={{ color: 'var(--text-faint)' }}>{spec.footnote}</div>}
      </div>
    );

  if (type === 'bar' && yKeys.length === 1 && !spec.stacked) {
    return wrap3d(<Bar3D data={to3dRows(yKeys[0])} ramp={spec.ramp ?? 0} maxBars={20} onSelect={onSelect} activeLabel={activeLabel} />, height + 30);
  }
  if (type === 'pie') {
    return wrap3d(
      <Donut3D data={to3dRows(yKeys[0])} centerLabel={spec.centerLabel || yKeys[0].label}
        onSelect={onSelect} activeLabel={onSelect ? (activeLabel || '') : undefined} />,
      height + 60);
  }

  let chart = null;
  if (type === 'bar') {
    chart = (
      <BarChart data={data} margin={{ top: 6, right: 8, left: 0, bottom: 0 }} barCategoryGap="28%"
        style={onSelect ? { cursor: 'pointer' } : undefined}
        onClick={onSelect ? (e) => { if (e && e.activeLabel != null) onSelect(e.activeLabel); } : undefined}>
        {grid}{xAxis}{yAxis}{tip}{legend}{refLine}
        {yKeys.map((k) => (
          <Bar key={k.key} dataKey={k.key} name={k.label} fill={k.color}
            stackId={spec.stacked ? 'stack' : undefined}
            radius={spec.stacked ? [0, 0, 0, 0] : [4, 4, 0, 0]} maxBarSize={38} />
        ))}
      </BarChart>
    );
  } else if (type === 'line' || type === 'area') {
    const Wrap = type === 'area' ? AreaChart : LineChart;
    chart = (
      <Wrap data={data} margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
        {grid}{xAxis}{yAxis}{tip}{legend}{refLine}
        {yKeys.map((k) => type === 'area' ? (
          <Area key={k.key} dataKey={k.key} name={k.label} stroke={k.color} fill={k.color}
            fillOpacity={0.14} strokeWidth={2} dot={false}
            stackId={spec.stacked ? 'stack' : undefined} connectNulls={false} />
        ) : (
          <Line key={k.key} dataKey={k.key} name={k.label} stroke={k.color} strokeWidth={2}
            dot={data.length <= 16 ? { r: 2.6, strokeWidth: 0, fill: k.color } : false}
            activeDot={{ r: 4 }} connectNulls={false} />
        ))}
      </Wrap>
    );
  } else if (type === 'pie') {
    const k = yKeys[0];
    chart = (
      <PieChart margin={{ top: 4, right: 4, left: 4, bottom: 4 }}>
        <Tooltip content={<GlassTooltip />} />
        <Legend wrapperStyle={legendStyle} iconSize={9} />
        <Pie data={data} dataKey={k.key} nameKey={spec.xKey} innerRadius="52%" outerRadius="82%"
          paddingAngle={2} strokeWidth={2} stroke="#f6f2ea">
          {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Pie>
      </PieChart>
    );
  } else if (type === 'scatter') {
    const k = yKeys[0];
    chart = (
      <ScatterChart margin={{ top: 6, right: 8, left: 0, bottom: 0 }}>
        {grid}
        <XAxis dataKey={spec.xKey} type="number" tick={AXIS_TICK} tickLine={false}
          axisLine={{ stroke: 'rgba(15,23,42,0.15)' }}
          name={spec.xLabel || spec.xKey} />
        <YAxis dataKey={k.key} type="number" tick={AXIS_TICK} tickLine={false} axisLine={false}
          width={48} name={k.label} />
        <Tooltip content={<GlassTooltip />} cursor={{ strokeDasharray: '3 3' }} />
        <Scatter data={data} fill={k.color} fillOpacity={0.55} shape="circle" />
      </ScatterChart>
    );
  }

  if (bare) {
    return <ResponsiveContainer width="100%" height="100%">{chart}</ResponsiveContainer>;
  }
  return (
    <div className="mt-2 max-w-full animate-fade-up">
      <div className="text-[12.5px] font-bold mb-0.5" style={{ color: 'var(--brand)' }}>{spec.title || 'Chart'}</div>
      {spec.subtitle && <div className="text-[11px] mb-1.5" style={{ color: 'var(--text-dim)' }}>{spec.subtitle}</div>}
      <div className="rounded-xl px-2 pt-2 pb-1" style={{
        background: 'var(--glass-strong)', border: '1px solid var(--glass-border)',
        boxShadow: 'var(--glass-shadow)', backdropFilter: 'blur(14px)',
      }}>
        <ResponsiveContainer width="100%" height={height}>{chart}</ResponsiveContainer>
      </div>
      {spec.footnote && <div className="text-[10px] mt-1 px-1" style={{ color: 'var(--text-faint)' }}>{spec.footnote}</div>}
    </div>
  );
}
