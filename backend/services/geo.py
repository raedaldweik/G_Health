"""
Nabd — geography of the gap.

Facility coordinates + per-facility outcome metrics for the map layer, and the
`map_spec` helper the agent's render_map tool and the scripted scenarios use to
put a colour-coded facility map inside a chat answer.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from services import hie, ml

# Approximate real-world coordinates (lat, lon) for the HMC / PHCC network.
FACILITY_COORDS = {
    "F001": (25.2966, 51.5017), "F002": (25.2992, 51.4986), "F003": (25.1714, 51.5931),
    "F004": (25.6869, 51.5071), "F005": (25.2087, 51.4163), "F006": (25.3237, 51.5296),
    "F007": (25.2905, 51.4362), "F008": (25.2841, 51.5459), "F009": (25.2375, 51.4893),
    "F010": (25.3231, 51.3915), "F011": (25.2331, 51.5342), "F012": (25.2778, 51.5178),
    "F013": (25.4301, 51.4892), "F014": (25.1662, 51.6018), "F015": (25.3752, 51.4903),
    "F016": (25.3554, 51.4712), "F017": (25.2648, 51.4207), "F018": (26.1292, 51.2105),
}

METRICS = {
    "pct_controlled": {"label": "% well-controlled (diabetes)", "worse_is_high": False, "fmt": "pct"},
    "gaps_per_100":   {"label": "Open care gaps per 100 patients", "worse_is_high": True, "fmt": "num"},
    "hba1c_overdue":  {"label": "HbA1c-overdue patients", "worse_is_high": True, "fmt": "int"},
    "mean_risk_pct":  {"label": "Mean 12-mo event risk (model)", "worse_is_high": True, "fmt": "pct"},
    "mean_cost":      {"label": "Mean annual cost per patient (QAR)", "worse_is_high": True, "fmt": "qar"},
    "mean_hba1c":     {"label": "Mean HbA1c", "worse_is_high": True, "fmt": "num"},
}


@lru_cache(maxsize=1)
def facility_metrics() -> list[dict]:
    s = hie.summary().copy()
    s = s[s["consent_status"] != "restricted"]
    s["risk_prob"] = ml._score(ml._feature_frame(s))
    fac = hie.tables()["facilities"]
    out = []
    for f in fac.itertuples():
        g = s[s["primary_facility_id"] == f.facility_id]
        dm = g[g["diabetes_type"] != "none"]
        lat, lon = FACILITY_COORDS[f.facility_id]
        out.append({
            "facility_id": f.facility_id, "name": f.facility_name, "type": f.facility_type,
            "region": f.region, "lat": lat, "lon": lon,
            "patients": int(len(g)),
            "pct_controlled": round(float((dm["glycaemic_control"] == "well_controlled").mean()) * 100, 1) if len(dm) else 0.0,
            "mean_hba1c": round(float(dm["hba1c_latest"].mean()), 2) if len(dm) else None,
            "gaps_per_100": round(float(g["care_gap_count"].sum()) / max(len(g), 1) * 100, 1),
            "hba1c_overdue": int(g["open_care_gaps"].str.contains("hba1c_overdue", na=False).sum()),
            "mean_risk_pct": round(float(g["risk_prob"].mean()) * 100, 1),
            "mean_cost": int(g["annual_cost_qar"].mean()),
            "admissions_12mo": int(g["admissions_12mo"].sum()),
            "expat_share_pct": round(float((g["nationality"] != "Qatari").mean()) * 100, 1),
        })
    med = float(np.median([o["pct_controlled"] for o in out]))
    for o in out:
        o["status"] = ("top" if o["pct_controlled"] >= med + 3 else
                       "flagged" if o["pct_controlled"] <= med - 3 else "on_target")
    return out


def region_rollup() -> list[dict]:
    fm = facility_metrics()
    regions = {}
    for o in fm:
        r = regions.setdefault(o["region"], {"region": o["region"], "patients": 0, "gaps": 0.0,
                                            "hba1c_overdue": 0, "ctrl_w": 0.0, "risk_w": 0.0})
        r["patients"] += o["patients"]
        r["gaps"] += o["gaps_per_100"] * o["patients"] / 100
        r["hba1c_overdue"] += o["hba1c_overdue"]
        r["ctrl_w"] += o["pct_controlled"] * o["patients"]
        r["risk_w"] += o["mean_risk_pct"] * o["patients"]
    rows = []
    for r in regions.values():
        n = max(r["patients"], 1)
        rows.append({"region": r["region"], "patients": r["patients"],
                     "gaps_per_100": round(r["gaps"] / n * 100, 1),
                     "hba1c_overdue": r["hba1c_overdue"],
                     "pct_controlled": round(r["ctrl_w"] / n, 1),
                     "mean_risk_pct": round(r["risk_w"] / n, 1)})
    return sorted(rows, key=lambda x: -x["gaps_per_100"])


def map_payload() -> dict:
    return {"facilities": facility_metrics(), "regions": region_rollup(),
            "metrics": {k: v["label"] for k, v in METRICS.items()},
            "metric_meta": METRICS}


def map_spec(facility_names: list[str] | None = None, metric: str = "pct_controlled",
             title: str | None = None, highlight: list[str] | None = None) -> dict:
    """A chat-renderable map spec: colour-coded facility circles for one metric."""
    metric = metric if metric in METRICS else "pct_controlled"
    fm = facility_metrics()
    if facility_names:
        keys = [n.lower() for n in facility_names]
        subset = [f for f in fm if any(k in f["name"].lower() or k == f["facility_id"].lower() for k in keys)]
        if not subset:
            subset = fm
    else:
        subset = fm
    meta = METRICS[metric]
    return {
        "type": "map",
        "title": title or f"{meta['label']} by facility",
        "metric": metric, "metric_label": meta["label"], "worse_is_high": meta["worse_is_high"],
        "facilities": [{"name": f["name"], "facility_id": f["facility_id"], "lat": f["lat"], "lon": f["lon"],
                        "region": f["region"], "type": f["type"], "patients": f["patients"],
                        "value": f[metric], "pct_controlled": f["pct_controlled"],
                        "gaps_per_100": f["gaps_per_100"], "hba1c_overdue": f["hba1c_overdue"],
                        "mean_risk_pct": f["mean_risk_pct"]} for f in subset],
        "highlight": highlight or [],
    }
