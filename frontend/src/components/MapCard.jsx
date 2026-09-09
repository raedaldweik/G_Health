import { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

/*
 * MapCard, a colour-coded facility map of Qatar (MapLibre GL).
 *  - key-free light basemap (CARTO Positron raster), matching the pearl glass
 *  - facility circles sized by patients, coloured sand → maroon by the metric
 *  - glass popups on hover, optional gold rings for highlighted facilities
 * Used by the Geography dashboard and by the agent's render_map chat cards.
 */

// Coarse Qatar peninsula outline (lon, lat), kept for the agent's offline map fallback.
export const QATAR_OUTLINE = [
  [50.80, 24.75], [50.78, 25.00], [50.82, 25.35], [50.88, 25.60], [51.00, 25.85],
  [51.10, 26.05], [51.22, 26.16], [51.40, 26.05], [51.55, 25.85], [51.62, 25.60],
  [51.55, 25.40], [51.62, 25.25], [51.60, 25.10], [51.55, 24.95], [51.50, 24.70],
  [51.30, 24.60], [51.00, 24.55], [50.80, 24.75],
];

// Basemap: OpenFreeMap's Positron style (vector tiles, no API key, no usage token).
// CARTO's raster basemaps now require an API key, which is why the tiles used to read
// "API KEY REQUIRED". Override at build time with VITE_BASEMAP_STYLE if the customer has
// their own tile service (a Google Maps Platform style, for example).
const STYLE = import.meta.env.VITE_BASEMAP_STYLE || 'https://tiles.openfreemap.org/styles/positron';

// Offline fallback: a soft land shape, no border, used only when the basemap fails to load.
const FALLBACK_STYLE = {
  version: 8,
  sources: { qatar: { type: 'geojson', data: { type: 'Feature', geometry: { type: 'Polygon', coordinates: [QATAR_OUTLINE] } } } },
  layers: [
    { id: 'bg', type: 'background', paint: { 'background-color': '#eef0f2' } },
    { id: 'land', type: 'fill', source: 'qatar', paint: { 'fill-color': '#f7f4ee', 'fill-opacity': 1 } },
  ],
};

// sand → maroon sequential ramp (worse = darker)
const RAMP = ['#efe1cf', '#e6b9c3', '#d17d99', '#b3466f', '#8A1538', '#4a0c20'];
const lerp = (a, b, t) => a + (b - a) * t;
const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
function rampColor(t) {
  const x = Math.max(0, Math.min(1, t)) * (RAMP.length - 1);
  const i = Math.min(Math.floor(x), RAMP.length - 2);
  const f = x - i;
  const [a, b] = [hex(RAMP[i]), hex(RAMP[i + 1])];
  return `rgb(${Math.round(lerp(a[0], b[0], f))},${Math.round(lerp(a[1], b[1], f))},${Math.round(lerp(a[2], b[2], f))})`;
}

const fmtVal = (v, metric) => {
  if (v == null) return 'n/a';
  if (metric === 'mean_cost') return `QAR ${Math.round(v).toLocaleString()}`;
  if (metric === 'pct_controlled' || metric === 'mean_risk_pct') return `${v}%`;
  return typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 1 }) : v;
};

export const VIEWS = {
  qatar: { bounds: [[50.55, 24.45], [51.85, 26.25]], padding: 18 },
  doha:  { bounds: [[51.30, 25.12], [51.66, 25.46]], padding: 30 },
};

export default function MapCard({ spec, height = 340, onSelect, selectedId, compact = false, view = 'qatar' }) {
  const elRef = useRef(null);
  const mapRef = useRef(null);
  const facilities = spec?.facilities || [];
  const metric = spec?.metric || 'pct_controlled';
  const worseIsHigh = spec?.worse_is_high ?? false;
  const highlight = new Set(spec?.highlight || []);

  // Build once
  useEffect(() => {
    if (!elRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: elRef.current, style: STYLE,
      bounds: [[50.55, 24.45], [51.85, 26.25]], fitBoundsOptions: { padding: 18 },
      attributionControl: false, dragRotate: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
    // Facility layers are installed on every style load, so they survive a swap to the
    // offline fallback style if the basemap cannot be fetched.
    const install = () => {
      if (map.getSource('fac')) return;
      map.addSource('fac', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
      map.addLayer({ id: 'fac-glow', type: 'circle', source: 'fac', paint: {
        'circle-radius': ['+', ['get', 'r'], 9], 'circle-color': ['get', 'color'], 'circle-opacity': 0.18, 'circle-blur': 0.6 } });
      map.addLayer({ id: 'fac-ring', type: 'circle', source: 'fac', filter: ['==', ['get', 'hl'], 1], paint: {
        'circle-radius': ['+', ['get', 'r'], 7], 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#b8862e', 'circle-stroke-width': 2.5 } });
      map.addLayer({ id: 'fac-dot', type: 'circle', source: 'fac', paint: {
        'circle-radius': ['get', 'r'], 'circle-color': ['get', 'color'], 'circle-opacity': 0.9,
        'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 } });
      map.addLayer({ id: 'fac-sel', type: 'circle', source: 'fac', filter: ['==', ['get', 'sel'], 1], paint: {
        'circle-radius': ['+', ['get', 'r'], 4], 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-color': '#0a1628', 'circle-stroke-width': 2 } });
      map.__ready = true;
      map.fire('nabd:refresh');
    };
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 14, className: 'mc-popup' });
    map.on('mousemove', 'fac-dot', (e) => {
      const p = e.features[0].properties;
      map.getCanvas().style.cursor = 'pointer';
      popup.setLngLat(e.lngLat).setHTML(`
        <div class="mc-pop-title">${p.name}</div>
        <div class="mc-pop-row"><span class="mc-k">${p.metric_label}</span><b>${p.value_fmt}</b></div>
        <div class="mc-pop-row"><span class="mc-k">Patients</span>${p.patients}</div>
        <div class="mc-pop-row"><span class="mc-k">Controlled</span>${p.pct_controlled}% · <span class="mc-k">Gaps/100</span>${p.gaps_per_100}</div>
        <div class="mc-pop-row"><span class="mc-k">HbA1c overdue</span>${p.hba1c_overdue} · <span class="mc-k">Mean risk</span>${p.mean_risk_pct}%</div>
        <div class="mc-pop-row"><span class="mc-k">${p.type}</span>${p.region}</div>`).addTo(map);
    });
    map.on('mouseleave', 'fac-dot', () => { map.getCanvas().style.cursor = ''; popup.remove(); });
    map.on('click', 'fac-dot', (e) => onSelect?.(e.features[0].properties.facility_id));
    map.on('load', install);
    map.on('style.load', install);
    // Basemap fallback: if the style or its tiles cannot be fetched (no internet, blocked
    // host), draw the peninsula as a soft land shape so the facility circles still make sense.
    let fell = false;
    const fallback = () => {
      if (fell || map.__ready) return;
      fell = true;
      map.setStyle(FALLBACK_STYLE);
    };
    map.on('error', (e) => { if (!map.__ready && /style|fetch|load/i.test(String(e?.error?.message || ''))) setTimeout(fallback, 1500); });
    const timer = setTimeout(fallback, 12000);
    mapRef.current = map;
    return () => { clearTimeout(timer); map.remove(); mapRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Push data whenever the spec/selection changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const src = map.getSource('fac');
      if (!src) return;
      const vals = facilities.map((f) => f.value).filter((v) => v != null);
      const lo = Math.min(...vals), hi = Math.max(...vals);
      const maxP = Math.max(...facilities.map((f) => f.patients || 1));
      src.setData({
        type: 'FeatureCollection',
        features: facilities.map((f) => {
          let t = hi > lo ? (f.value - lo) / (hi - lo) : 0.5;
          if (!worseIsHigh) t = 1 - t;
          return {
            type: 'Feature', geometry: { type: 'Point', coordinates: [f.lon, f.lat] },
            properties: {
              ...f, metric_label: spec.metric_label, value_fmt: fmtVal(f.value, metric),
              color: rampColor(t), r: 7 + 13 * Math.sqrt((f.patients || 1) / maxP),
              hl: highlight.has(f.name) ? 1 : 0, sel: f.facility_id === selectedId ? 1 : 0,
            },
          };
        }),
      });
    };
    if (map.__ready) apply(); else map.once('nabd:refresh', apply);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spec, selectedId]);

  // Fly between the country view and Greater Doha
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const v = VIEWS[view] || VIEWS.qatar;
    const go = () => map.fitBounds(v.bounds, { padding: v.padding, duration: 900 });
    if (map.__ready) go(); else map.once('nabd:refresh', go);
  }, [view]);

  if (!facilities.length) return null;
  const inner = (
    <div className="mc-frame" style={{ height }}>
      <div ref={elRef} className="mc-map" style={{ height: '100%' }} />
      <div className="mc-legend">
        <span className="mc-legend-lbl">{worseIsHigh ? 'lower' : 'better'}</span>
        <span className="mc-legend-bar" />
        <span className="mc-legend-lbl">{worseIsHigh ? 'higher' : 'worse'}</span>
        <span className="mc-legend-metric">{spec.metric_label}</span>
      </div>
    </div>
  );
  if (compact) return inner;
  return (
    <div className="mc-wrap animate-fade-up">
      <div className="mc-title">{spec.title || 'Facility map'}</div>
      {inner}
    </div>
  );
}
