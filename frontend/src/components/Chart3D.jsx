import { useId, useMemo, useRef, useState } from 'react';

/*
 * Chart3D — faithful React ports of the reports repository's signature charts:
 *   Bar3D    isometric bars (front/side/top faces, sheen, shadow, staggered pop-in)
 *   Donut3D  tilted ring (per-segment top gradients, depth walls, sheen, legend chips)
 * Same geometry, gradients and interaction language as bar.html / donut.html.
 */

// The reports 4-step colour ramps (light → dark), verbatim.
export const RAMPS = [
  ['#f4b6c8', '#d15a82', '#9b1c46', '#4a0c20'],   // qatar maroon
  ['#ffe1a8', '#ebbf6a', '#b8862e', '#7a571a'],   // honey gold
  ['#d8c5f5', '#a98ae0', '#6d4fa8', '#3f2a6b'],   // violet
  ['#a8f5b8', '#6ddc8a', '#3a8e5a', '#1f5a36'],   // emerald
  ['#ffd0a8', '#fb923c', '#b06024', '#6e3a12'],   // amber
  ['#f5c0dc', '#e07ab2', '#a8407a', '#651f47'],   // rose
  ['#ffb8b8', '#f08585', '#b03c3c', '#6f1f1f'],   // crimson
  ['#f7e8a8', '#e3cb5d', '#a8902a', '#6b5a14'],   // citrine
  ['#e9d9c8', '#c9a98a', '#8a6a4e', '#4e3728'],   // desert sand
  ['#c2ecec', '#72cfc9', '#2d8f88', '#15534e'],   // sea (last resort)
];

export function fmt3d(v) {
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
  if (a >= 1e3) return (v / 1e3).toFixed(1).replace(/\.0$/, '') + 'k';
  if (a > 0 && a < 10 && v !== Math.round(v)) return v.toFixed(1);
  return Math.round(v).toLocaleString();
}

function niceCeil(v) {
  if (v <= 0) return 1;
  const exp = Math.floor(Math.log10(v));
  const f = v / Math.pow(10, exp);
  const nf = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 3 ? 3
    : f <= 4 ? 4 : f <= 5 ? 5 : f <= 6 ? 6 : f <= 8 ? 8 : 10;
  return nf * Math.pow(10, exp);
}

const truncate = (s, n) => (s.length > n ? s.slice(0, n - 1) + '…' : s);

/* ─────────────────────────── Bar3D ───────────────────────────
 * data: [{ label, value }] · ramp: index into RAMPS (default teal)
 * The full render3DBars visual language from bar.html. */
export function Bar3D({ data, ramp = 0, maxBars = 12, height = '100%', unit = '' }) {
  const uid = useId().replace(/[:]/g, '');
  const wrapRef = useRef(null);
  const [tip, setTip] = useState(null);

  const items = useMemo(() => {
    let rows = (data || []).filter((d) => d && d.value != null && isFinite(d.value));
    if (rows.length > maxBars) {
      const head = rows.slice(0, maxBars - 1);
      const tail = rows.slice(maxBars - 1);
      head.push({ label: 'Other', value: tail.reduce((s, d) => s + d.value, 0) });
      rows = head;
    }
    return rows;
  }, [data, maxBars]);

  if (!items.length) return null;
  const s = RAMPS[ramp % RAMPS.length];
  const grandTotal = items.reduce((sum, d) => sum + d.value, 0);

  const VB = { w: 1000, h: 480 };
  const padL = 64, padR = 30, padT = 46, padB = 58;
  const chartW = VB.w - padL - padR;
  const chartH = VB.h - padT - padB;
  const n = items.length;
  const BAR_W = Math.max(26, Math.min(96, (chartW * 0.62) / n));
  const CAT_GAP = (chartW - n * BAR_W) / (n + 1);
  const ISO_X = Math.max(5, BAR_W * 0.16);
  const ISO_Y = Math.max(7, BAR_W * 0.20);
  const maxV = niceCeil(Math.max(...items.map((d) => d.value), 0) || 1);
  const baseY = padT + chartH;
  const gridSteps = 4;

  const showTip = (e, d) => {
    const rect = wrapRef.current?.getBoundingClientRect();
    if (!rect) return;
    setTip({
      x: Math.min(e.clientX - rect.left + 14, rect.width - 165),
      label: d.label, value: d.value,
      pct: grandTotal > 0 ? ((d.value / grandTotal) * 100).toFixed(1) : '0.0',
    });
  };

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%', height }}>
      <svg viewBox={`0 0 ${VB.w} ${VB.h}`} preserveAspectRatio="xMidYMid meet"
        style={{ width: '100%', height: '100%' }}>
        <defs>
          <radialGradient id={`b3sh-${uid}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#000" stopOpacity="0.65" />
            <stop offset="60%" stopColor="#000" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#000" stopOpacity="0" />
          </radialGradient>
          <linearGradient id={`b3sheen-${uid}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#fff" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#fff" stopOpacity="0" />
          </linearGradient>
          <linearGradient id={`b3f-${uid}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={s[0]} /><stop offset="55%" stopColor={s[1]} />
            <stop offset="100%" stopColor={s[2]} />
          </linearGradient>
          <linearGradient id={`b3s-${uid}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={s[1]} /><stop offset="60%" stopColor={s[2]} />
            <stop offset="100%" stopColor={s[3]} />
          </linearGradient>
          <radialGradient id={`b3t-${uid}`} cx="35%" cy="30%" r="80%">
            <stop offset="0%" stopColor={s[0]} /><stop offset="55%" stopColor={s[1]} />
            <stop offset="100%" stopColor={s[2]} />
          </radialGradient>
        </defs>

        {Array.from({ length: gridSteps + 1 }, (_, i) => {
          const y = padT + chartH - (chartH * i) / gridSteps;
          return (
            <g key={i}>
              <line x1={padL} x2={padL + chartW} y1={y} y2={y} className="v3d-grid-line" />
              <text x={padL - 8} y={y + 4} textAnchor="end" className="v3d-y-label">
                {fmt3d((maxV * i) / gridSteps)}
              </text>
            </g>
          );
        })}

        {items.map((d, ci) => {
          const barX = padL + CAT_GAP + ci * (BAR_W + CAT_GAP);
          const barH = Math.max(0, (d.value / maxV) * chartH);
          const barY = baseY - barH;
          return (
            <g key={ci}>
              <g className="v3d-stack-group v3d-bar-group"
                style={{ animationDelay: `${0.15 + ci * 0.06}s` }}
                onMouseMove={(e) => showTip(e, d)} onMouseLeave={() => setTip(null)}>
                <ellipse cx={barX + BAR_W / 2 + ISO_X / 2} cy={baseY + ISO_Y + 2}
                  rx={BAR_W * 0.62} ry={ISO_Y * 0.7} fill={`url(#b3sh-${uid})`} opacity="0.5" />
                <polygon fill={`url(#b3s-${uid})`} stroke={s[3]} strokeWidth="0.3" strokeOpacity="0.45"
                  points={`${barX + BAR_W},${baseY} ${barX + BAR_W + ISO_X},${baseY - ISO_Y} ${barX + BAR_W + ISO_X},${barY - ISO_Y} ${barX + BAR_W},${barY}`} />
                <rect x={barX} y={barY} width={BAR_W} height={barH}
                  fill={`url(#b3f-${uid})`} stroke={s[2]} strokeWidth="0.3" strokeOpacity="0.4" />
                <rect x={barX} y={barY} width={Math.max(2, BAR_W * 0.05)} height={barH}
                  fill={`url(#b3sheen-${uid})`} opacity="0.6" />
                <polygon fill={`url(#b3t-${uid})`} stroke={s[2]} strokeWidth="0.3" strokeOpacity="0.45"
                  points={`${barX},${barY} ${barX + BAR_W},${barY} ${barX + BAR_W + ISO_X},${barY - ISO_Y} ${barX + ISO_X},${barY - ISO_Y}`} />
                <text x={barX + BAR_W / 2 + ISO_X / 2} y={barY - ISO_Y - 8}
                  textAnchor="middle" className="v3d-bar-total">
                  {fmt3d(d.value)}{unit}
                </text>
                <rect className="v3d-hit" x={barX - CAT_GAP / 2} y={padT}
                  width={BAR_W + CAT_GAP} height={chartH + ISO_Y + 6} />
              </g>
              <text x={barX + BAR_W / 2 + ISO_X / 2} y={baseY + ISO_Y + 24}
                textAnchor="middle" className="v3d-axis-label">
                {truncate(String(d.label), Math.max(6, Math.round(BAR_W / 6)))}
              </text>
            </g>
          );
        })}
      </svg>

      {tip && (
        <div className="v3d-tooltip visible" style={{ left: tip.x, top: 6 }}>
          <div className="v3d-tooltip-title">{tip.label}</div>
          <div className="v3d-tooltip-row">
            <span className="v3d-tooltip-dot" style={{ background: s[2] }} />
            <span className="v3d-tooltip-label">Value</span>
            <span className="v3d-tooltip-val">{tip.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}{unit}</span>
          </div>
          <div className="v3d-tooltip-row">
            <span className="v3d-tooltip-dot" style={{ background: 'transparent', border: '1px solid var(--ink-5, #94a3b8)' }} />
            <span className="v3d-tooltip-label">Share</span>
            <span className="v3d-tooltip-val">{tip.pct}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────── Donut3D ───────────────────────────
 * data: [{ label, value }] — tilted 3D ring with depth walls, sheen,
 * centre total and clickable legend chips (donut.html, verbatim geometry). */
export function Donut3D({ data, centerLabel = 'Total', centerValue = null, height = '100%',
                          showLegend = true, valueFormatter = fmt3d }) {
  const uid = useId().replace(/[:]/g, '');
  const [activeKey, setActiveKey] = useState('');

  const items = useMemo(() => (data || [])
    .filter((d) => d && d.value > 0.0001)
    .map((d, i) => ({ ...d, key: String(d.label),
                      color: RAMPS[(d.ramp ?? i) % RAMPS.length] })), [data]);

  if (!items.length) return null;
  const total = items.reduce((s, d) => s + d.value, 0);

  const VB = { w: 220, h: 148 };
  const cx = 110, cy = 64, rOuter = 82, rInner = 50, tilt = 0.42, depth = 15;
  const pt = (angle, r, yOff = 0) => [cx + r * Math.cos(angle), cy + r * Math.sin(angle) * tilt + yOff];

  let acc = -Math.PI / 2;
  const segments = items.map((d) => {
    const start = acc;
    let span = (d.value / total) * Math.PI * 2;
    if (items.length === 1) span = Math.PI * 2 - 0.0001;
    const end = start + span;
    acc = end;
    return { ...d, start, end, midAngle: (start + end) / 2 };
  });

  const topFace = (a1, a2) => {
    const [p1x, p1y] = pt(a1, rOuter); const [p2x, p2y] = pt(a2, rOuter);
    const [p3x, p3y] = pt(a2, rInner); const [p4x, p4y] = pt(a1, rInner);
    const la = a2 - a1 > Math.PI ? 1 : 0;
    return `M ${p1x} ${p1y} A ${rOuter} ${rOuter * tilt} 0 ${la} 1 ${p2x} ${p2y} L ${p3x} ${p3y} A ${rInner} ${rInner * tilt} 0 ${la} 0 ${p4x} ${p4y} Z`;
  };
  const fullRing = () => {
    const oL = pt(Math.PI, rOuter), oR = pt(0, rOuter), iL = pt(Math.PI, rInner), iR = pt(0, rInner);
    return `M ${oL[0]} ${oL[1]} A ${rOuter} ${rOuter * tilt} 0 1 1 ${oR[0]} ${oR[1]} A ${rOuter} ${rOuter * tilt} 0 1 1 ${oL[0]} ${oL[1]}
            M ${iL[0]} ${iL[1]} A ${rInner} ${rInner * tilt} 0 1 0 ${iR[0]} ${iR[1]} A ${rInner} ${rInner * tilt} 0 1 0 ${iL[0]} ${iL[1]} Z`;
  };
  const sideWall = (a1, a2) => {
    const st = Math.max(a1, 0), en = Math.min(a2, Math.PI);
    if (st >= en) return null;
    const [p1x, p1y] = pt(st, rOuter); const [p2x, p2y] = pt(en, rOuter);
    const [p3x, p3y] = pt(en, rOuter, depth); const [p4x, p4y] = pt(st, rOuter, depth);
    const la = en - st > Math.PI ? 1 : 0;
    return `M ${p1x} ${p1y} A ${rOuter} ${rOuter * tilt} 0 ${la} 1 ${p2x} ${p2y} L ${p3x} ${p3y} A ${rOuter} ${rOuter * tilt} 0 ${la} 0 ${p4x} ${p4y} Z`;
  };
  const sheenPath = (a1, a2) => {
    const st = Math.max(a1, -Math.PI), en = Math.min(a2, 0);
    if (st >= en) return null;
    const rIn2 = rOuter - 4;
    const [p1x, p1y] = pt(st, rOuter); const [p2x, p2y] = pt(en, rOuter);
    const [p3x, p3y] = pt(en, rIn2); const [p4x, p4y] = pt(st, rIn2);
    const la = en - st > Math.PI ? 1 : 0;
    return `M ${p1x} ${p1y} A ${rOuter} ${rOuter * tilt} 0 ${la} 1 ${p2x} ${p2y} L ${p3x} ${p3y} A ${rIn2} ${rIn2 * tilt} 0 ${la} 0 ${p4x} ${p4y} Z`;
  };

  const walls = [...segments].map((seg, i) => ({ ...seg, idx: i }))
    .sort((a, b) => Math.sin(a.midAngle) - Math.sin(b.midAngle));
  const toggle = (seg) => setActiveKey(activeKey === seg.key ? '' : seg.key);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height, minHeight: 0 }}>
      <div style={{ position: 'relative', flex: '1 1 auto', minHeight: 0 }}>
        <svg viewBox={`0 0 ${VB.w} ${VB.h}`} preserveAspectRatio="xMidYMid meet"
          style={{ width: '100%', height: '100%' }}>
          <defs>
            <radialGradient id={`dsh-${uid}`} cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#000" stopOpacity="0.65" />
              <stop offset="60%" stopColor="#000" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#000" stopOpacity="0" />
            </radialGradient>
            {segments.map((d, i) => (
              <g key={i}>
                <radialGradient id={`dtop-${uid}-${i}`} cx="35%" cy="25%" r="80%">
                  <stop offset="0%" stopColor={d.color[0]} /><stop offset="55%" stopColor={d.color[1]} />
                  <stop offset="100%" stopColor={d.color[2]} />
                </radialGradient>
                <linearGradient id={`dside-${uid}-${i}`} x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor={d.color[1]} /><stop offset="55%" stopColor={d.color[2]} />
                  <stop offset="100%" stopColor={d.color[3]} />
                </linearGradient>
              </g>
            ))}
            <linearGradient id={`dsheen-${uid}`} x1="50%" y1="0%" x2="50%" y2="100%">
              <stop offset="0%" stopColor="#fff" stopOpacity="0.75" />
              <stop offset="50%" stopColor="#fff" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#fff" stopOpacity="0" />
            </linearGradient>
          </defs>

          <ellipse cx={cx} cy={cy + depth + 6} rx={rOuter * 0.92} ry={rOuter * tilt * 0.55}
            fill={`url(#dsh-${uid})`} opacity="0.5" />

          {walls.map((seg) => {
            const d = sideWall(seg.start, seg.end);
            return d ? (
              <path key={`w${seg.idx}`} d={d} fill={`url(#dside-${uid}-${seg.idx})`}
                stroke={seg.color[3]} strokeWidth="0.25" strokeOpacity="0.5" />
            ) : null;
          })}

          <ellipse cx={cx} cy={cy + 1.5} rx={rInner} ry={rInner * tilt} fill="none"
            stroke="#000" strokeWidth="3" strokeOpacity="0.35" style={{ filter: 'blur(0.8px)' }} />

          {segments.map((seg, i) => {
            const dimmed = activeKey && seg.key !== activeKey;
            const active = activeKey && seg.key === activeKey;
            const sheen = sheenPath(seg.start, seg.end);
            return (
              <g key={i} className="d3d-segment" style={{
                animationDelay: `${0.15 + i * 0.13}s`, color: seg.color[1],
                opacity: dimmed ? 0.35 : undefined, cursor: 'pointer',
                filter: active ? 'brightness(1.15) saturate(1.15) drop-shadow(0 0 6px currentColor)' : undefined,
              }} onClick={() => toggle(seg)}>
                <path d={items.length === 1 ? fullRing() : topFace(seg.start, seg.end)}
                  fillRule={items.length === 1 ? 'evenodd' : undefined}
                  fill={`url(#dtop-${uid}-${i})`} className="d3d-top"
                  stroke={seg.color[2]} strokeWidth="0.3" strokeOpacity="0.5" />
                {sheen && <path d={sheen} fill={`url(#dsheen-${uid})`} opacity="0.6" style={{ pointerEvents: 'none' }} />}
                <title>{`${seg.label} — ${seg.value.toLocaleString(undefined, { maximumFractionDigits: 2 })} (${((seg.value / total) * 100).toFixed(1)}%)`}</title>
              </g>
            );
          })}
        </svg>
        <div className="donut-center">
          <div className="donut-center-val">
            {activeKey ? valueFormatter(items.find((d) => d.key === activeKey).value)
              : (centerValue ?? valueFormatter(total))}
          </div>
          <div className="donut-center-lbl">
            {activeKey || centerLabel}
          </div>
        </div>
      </div>

      {showLegend && (
        <div className="donut-legend">
          {items.map((d) => {
            const active = activeKey === d.key;
            const dimmed = activeKey && !active;
            return (
              <div key={d.key}
                className={`legend-chip${active ? ' active' : ''}${dimmed ? ' dimmed' : ''}`}
                style={{ color: d.color[2] }} onClick={() => toggle(d)}>
                <span className="legend-dot" style={{ background: d.color[1] }} />
                <span>{d.label}</span>
                <span className="legend-val">{valueFormatter(d.value)}</span>
                <span className="legend-pct">{((d.value / total) * 100).toFixed(1)}%</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
