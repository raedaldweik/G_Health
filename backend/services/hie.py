"""
Nabd — HIE query engine.

Loads the synthetic Health Information Exchange (8 relational tables) once and
exposes the structured query surface used by BOTH the agent tools and the
dashboard APIs — one source of truth, so the chat and the dashboards can never
disagree. Phase 2 swaps this module's internals for BigQuery SQL over the
streamed FHIR export; the function contracts stay the same.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data" / "hie"
TODAY = date(2026, 9, 1)

GAP_LABELS = {
    "hba1c_overdue": "HbA1c test overdue (>6 months)",
    "retinal_screening_overdue": "Retinal screening overdue (>12 months)",
    "foot_exam_overdue": "Diabetic foot exam overdue (>12 months)",
    "acr_screening_missing": "Urine ACR screening missing (12 months)",
    "statin_gap": "High CV risk with no statin therapy",
    "bp_uncontrolled": "Hypertension uncontrolled (≥140/90)",
    "glp1_sglt2_gap": "T2DM with obesity/CVD not on SGLT2i/GLP-1 RA",
    "hf_gdmt_gap": "HFrEF missing GDMT pillar(s)",
    "af_anticoagulation_gap": "Atrial fibrillation without anticoagulation",
}

_OPS = {
    "==": lambda s, v: s == v, "!=": lambda s, v: s != v,
    ">": lambda s, v: s > v, "<": lambda s, v: s < v,
    ">=": lambda s, v: s >= v, "<=": lambda s, v: s <= v,
    "contains": lambda s, v: s.astype(str).str.contains(str(v), case=False, na=False),
    "not_contains": lambda s, v: ~s.astype(str).str.contains(str(v), case=False, na=False),
    "in": lambda s, v: s.isin(v if isinstance(v, list) else [v]),
    "not_in": lambda s, v: ~s.isin(v if isinstance(v, list) else [v]),
    "between": lambda s, v: (s >= v[0]) & (s <= v[1]),
    "is_null": lambda s, v: s.isna(),
    "not_null": lambda s, v: s.notna(),
}


TABLE_NAMES = ["facilities", "patients", "conditions", "observations",
               "medications", "encounters", "care_gaps", "patient_summary"]


def _load_raw() -> dict[str, pd.DataFrame]:
    """Phase 2: BigQuery is the system of record. Phase 1 / fallback: the committed csv.gz."""
    from services import bq, platform as P
    if P.HIE_BACKEND == "bigquery":
        try:
            return bq.load_tables()
        except Exception as e:               # dataset empty (first boot) or unreachable
            bq.STATUS["error"] = f"{type(e).__name__}: {str(e)[:300]}"
            print(f"⚠ BigQuery unavailable ({bq.STATUS['error']}) — serving the local HIE files"
                  + (" and provisioning BigQuery in the background" if P.BQ_AUTOLOAD and P.PROJECT else ""),
                  flush=True)
            if P.BQ_AUTOLOAD and P.PROJECT and isinstance(e, LookupError):
                bq.provision_in_background()
    t = {name: pd.read_csv(DATA / f"{name}.csv.gz") for name in TABLE_NAMES}
    bq.STATUS["loaded_from"] = "local-csv"
    bq.STATUS["rows"] = {k: len(v) for k, v in t.items()}
    return t


@lru_cache(maxsize=1)
def tables() -> dict[str, pd.DataFrame]:
    t = _load_raw()
    for name, df in t.items():                       # BigQuery returns DATE objects; the engine expects strings
        for col in df.columns:
            if df[col].dtype == object and len(df) and hasattr(df[col].iloc[0], "isoformat"):
                t[name][col] = df[col].astype(str)
    # join facility names onto summary for friendlier grouping
    fac = t["facilities"][["facility_id", "facility_name", "facility_type", "region"]]
    t["patient_summary"] = t["patient_summary"].merge(
        fac, left_on="primary_facility_id", right_on="facility_id", how="left").drop(columns=["facility_id"])
    return t


def summary() -> pd.DataFrame:
    return tables()["patient_summary"]


@lru_cache(maxsize=1)
def data_dictionary() -> dict:
    return json.loads((DATA / "data_dictionary.json").read_text())


# ─────────────────────────── metadata / discovery ───────────────────────────

def describe_dataset() -> dict:
    t = tables()
    return {
        "tables": {name: {"rows": len(df), "description": data_dictionary().get(name, ""),
                          "columns": list(df.columns)} for name, df in t.items()},
        "note": ("patient_summary is the wide analytical table — use it for cohort filters, "
                 "group-bys and rankings. observations holds the longitudinal labs/vitals "
                 "(obs_key ∈ hba1c,fpg,sbp,dbp,ldl,hdl,tg,egfr,acr,bmi,ef)."),
    }


def describe_column(column: str, table: str = "patient_summary") -> dict:
    df = tables().get(table)
    if df is None or column not in df.columns:
        return {"error": f"column '{column}' not found in table '{table}'",
                "available_tables": list(tables().keys())}
    s = df[column]
    if pd.api.types.is_numeric_dtype(s):
        d = s.describe()
        return {"table": table, "column": column, "type": "numeric",
                "count": int(d["count"]), "mean": round(float(d["mean"]), 3),
                "std": round(float(d["std"]), 3), "min": float(d["min"]),
                "p25": float(d["25%"]), "median": float(d["50%"]),
                "p75": float(d["75%"]), "max": float(d["max"]),
                "missing": int(s.isna().sum())}
    vc = s.value_counts().head(15)
    return {"table": table, "column": column, "type": "categorical",
            "distinct": int(s.nunique()), "top_values": {str(k): int(v) for k, v in vc.items()},
            "missing": int(s.isna().sum())}


# ─────────────────────────── patient-level access ───────────────────────────

def get_patient(patient_id: str) -> dict:
    t = tables()
    s = summary()
    row = s[s["patient_id"] == patient_id]
    if row.empty:
        return {"found": False, "patient_id": patient_id}
    r = row.iloc[0]
    if r["consent_status"] == "restricted":
        # Consent enforcement: the agent may not read a restricted record.
        # (Phase 2: Cloud Healthcare API FHIR consent enforcement does this natively.)
        return {"found": True, "consent": "DENIED",
                "message": ("Patient consent status is RESTRICTED — record access blocked "
                            "by the HIE consent policy. This denial has been logged.")}
    conds = t["conditions"].query("patient_id == @patient_id")
    meds = t["medications"].query("patient_id == @patient_id and status == 'active'")
    recent_enc = (t["encounters"].query("patient_id == @patient_id")
                  .sort_values("start_date").tail(6))
    rec = {k: (None if (isinstance(v, float) and np.isnan(v)) else
               (v.item() if hasattr(v, "item") else v)) for k, v in r.items()}
    rec.pop("event_probability_true", None)   # hidden ground truth never leaves the service
    rec.pop("event_next_12m", None)
    return {
        "found": True, "consent": "general", "patient": rec,
        "conditions": conds[["condition", "icd10_code", "snomed_code", "onset_date"]].to_dict("records"),
        "active_medications": meds[["medication", "atc_code", "drug_class", "start_date"]].to_dict("records"),
        "recent_encounters": recent_enc[["start_date", "encounter_type", "reason",
                                         "facility_id", "length_of_stay_days"]].to_dict("records"),
    }


def patient_timeline(patient_id: str, obs_keys: list[str] | None = None) -> dict:
    obs = tables()["observations"]
    rows = obs[obs["patient_id"] == patient_id]
    if obs_keys:
        rows = rows[rows["obs_key"].isin(obs_keys)]
    out = {}
    for key, grp in rows.groupby("obs_key"):
        out[key] = [{"date": d, "value": float(v)}
                    for d, v in zip(grp["effective_date"], grp["value"])]
    return {"patient_id": patient_id, "series": out}


# ─────────────────────────── cohort query surface ───────────────────────────

def _apply_filters(df: pd.DataFrame, filters: list[dict] | None) -> pd.DataFrame:
    if not filters:
        return df
    mask = pd.Series(True, index=df.index)
    for f in filters:
        col, op, val = f.get("column"), f.get("op", "=="), f.get("value")
        if col not in df.columns:
            raise ValueError(f"unknown column '{col}' — call describe_dataset for the schema")
        if op not in _OPS:
            raise ValueError(f"unknown operator '{op}'")
        mask &= _OPS[op](df[col], val)
    return df[mask]


def filter_cohort(filters: list[dict] | None = None, select_columns: list[str] | None = None,
                  aggregate: dict | None = None, limit: int = 20) -> dict:
    df = _apply_filters(summary(), filters)
    out: dict[str, Any] = {"matched": int(len(df))}
    if aggregate and aggregate.get("column"):
        col, func = aggregate["column"], aggregate.get("func", "mean")
        if col in df.columns:
            out["aggregate"] = {"column": col, "func": func,
                                "value": round(float(getattr(df[col], func)()), 3)}
    if select_columns:
        cols = [c for c in select_columns if c in df.columns]
        if "patient_id" not in cols:
            cols = ["patient_id"] + cols
        out["rows"] = df[cols].head(limit).replace({np.nan: None}).to_dict("records")
    return out


def groupby_aggregate(group_by: str, metric: str | None = None, func: str = "mean",
                      filters: list[dict] | None = None, top: int = 30) -> dict:
    df = _apply_filters(summary(), filters)
    if group_by not in df.columns:
        return {"error": f"unknown column '{group_by}'"}
    if metric and metric in df.columns:
        g = getattr(df.groupby(group_by)[metric], func)().round(3)
    else:
        g = df.groupby(group_by).size()
        metric, func = "patients", "count"
    g = g.sort_values(ascending=False).head(top)
    return {"group_by": group_by, "metric": metric, "func": func,
            "rows": [{"group": str(k), "value": (v.item() if hasattr(v, "item") else v)}
                     for k, v in g.items()]}


def top_n(sort_by: str, n: int = 10, ascending: bool = False,
          filters: list[dict] | None = None, select_columns: list[str] | None = None) -> dict:
    df = _apply_filters(summary(), filters)
    if sort_by not in df.columns:
        return {"error": f"unknown column '{sort_by}'"}
    cols = select_columns or ["patient_id", "full_name", "age", "nationality", "facility_name",
                              "hba1c_latest", "cv_risk_band", "annual_cost_qar", "care_gap_count"]
    cols = [c for c in dict.fromkeys(["patient_id"] + cols + [sort_by]) if c in df.columns]
    rows = df.sort_values(sort_by, ascending=ascending).head(n)[cols]
    return {"rows": rows.replace({np.nan: None}).to_dict("records")}


def correlate(col_a: str, col_b: str, filters: list[dict] | None = None) -> dict:
    df = _apply_filters(summary(), filters)
    if col_a not in df.columns or col_b not in df.columns:
        return {"error": "unknown column(s)"}
    sub = df[[col_a, col_b]].dropna()
    r = float(sub[col_a].corr(sub[col_b]))
    return {"col_a": col_a, "col_b": col_b, "pearson_r": round(r, 3), "n": len(sub)}


def histogram(column: str, bins: int = 10, filters: list[dict] | None = None) -> dict:
    df = _apply_filters(summary(), filters)
    if column not in df.columns:
        return {"error": f"unknown column '{column}'"}
    s = df[column].dropna()
    counts, edges = np.histogram(s, bins=bins)
    return {"column": column,
            "bins": [{"range": f"{edges[i]:.1f}–{edges[i+1]:.1f}", "count": int(c)}
                     for i, c in enumerate(counts)]}


# ─────────────────────────── pre-built population views ───────────────────────────

def cohort_stats() -> dict:
    s = summary()
    dm = s[s["diabetes_type"] != "none"]
    return {
        "patients": len(s), "with_diabetes": len(dm),
        "mean_hba1c": round(float(dm["hba1c_latest"].mean()), 2),
        "pct_well_controlled": round(float((dm["glycaemic_control"] == "well_controlled").mean()) * 100, 1),
        "pct_uncontrolled": round(float((dm["glycaemic_control"] == "uncontrolled").mean()) * 100, 1),
        "pct_established_cvd": round(float(s["established_cvd"].mean()) * 100, 1),
        "mean_ascvd_10yr_pct": round(float(s["ascvd_10yr_pct"].mean()), 1),
        "statin_gap_patients": int(s["open_care_gaps"].str.contains("statin_gap", na=False).sum()),
        "bp_uncontrolled_patients": int(s["open_care_gaps"].str.contains("bp_uncontrolled", na=False).sum()),
        "af_anticoag_gap_patients": int(s["open_care_gaps"].str.contains("af_anticoagulation_gap", na=False).sum()),
        "total_open_care_gaps": int(s["care_gap_count"].sum()),
        "total_annual_cost_qar": int(s["annual_cost_qar"].sum()),
        "admissions_12mo": int(s["admissions_12mo"].sum()),
        "ed_visits_12mo": int(s["ed_visits_12mo"].sum()),
    }


def hba1c_trend_monthly() -> list[dict]:
    obs = tables()["observations"]
    h = obs[obs["obs_key"] == "hba1c"].copy()
    h["month"] = h["effective_date"].str[:7]
    g = h.groupby("month")["value"].agg(["mean", "count"])
    g = g[g["count"] >= 30]
    return [{"month": m, "mean_hba1c": round(float(r["mean"]), 2), "tests": int(r["count"])}
            for m, r in g.iterrows()]


def facility_benchmark() -> list[dict]:
    s = summary()
    dm = s[s["diabetes_type"] != "none"]
    g = dm.groupby(["facility_name", "facility_type"]).agg(
        patients=("patient_id", "count"),
        mean_hba1c=("hba1c_latest", "mean"),
        pct_controlled=("glycaemic_control", lambda x: (x == "well_controlled").mean() * 100),
        mean_gaps=("care_gap_count", "mean"),
        mean_cost=("annual_cost_qar", "mean"),
    ).round(2).reset_index()
    g = g.sort_values("pct_controlled", ascending=False)
    med = g["pct_controlled"].median()
    g["status"] = np.where(g["pct_controlled"] >= med + 3, "top",
                           np.where(g["pct_controlled"] <= med - 3, "flagged", "on_target"))
    return g.to_dict("records")


def equity_breakdown() -> list[dict]:
    s = summary()
    dm = s[s["diabetes_type"] != "none"]
    g = dm.groupby("nationality").agg(
        patients=("patient_id", "count"),
        mean_hba1c=("hba1c_latest", "mean"),
        pct_controlled=("glycaemic_control", lambda x: (x == "well_controlled").mean() * 100),
        mean_gaps=("care_gap_count", "mean"),
        mean_cost=("annual_cost_qar", "mean"),
    ).round(2).reset_index().sort_values("mean_hba1c", ascending=False)
    return g.to_dict("records")


def cvd_risk_distribution() -> list[dict]:
    g = summary()["cv_risk_band"].value_counts()
    order = ["Low", "Moderate", "High", "Very High"]
    return [{"band": b, "patients": int(g.get(b, 0))} for b in order]


def cvd_prevalence() -> list[dict]:
    s = summary()
    conds = [("Hypertension", "htn"), ("Dyslipidaemia", "dyslipidemia"),
             ("Coronary artery disease", "cad"), ("Heart failure", "hf"),
             ("Prior stroke/TIA", "stroke"), ("Peripheral arterial disease", "pad"),
             ("Atrial fibrillation", "af"), ("Established CVD (any)", "established_cvd")]
    return [{"condition": label, "patients": int(s[c].sum()),
             "prevalence_pct": round(float(s[c].mean()) * 100, 1)} for label, c in conds]


def care_gap_summary() -> list[dict]:
    gaps = tables()["care_gaps"]
    g = gaps.groupby(["gap_key", "gap_label"]).size().sort_values(ascending=False)
    return [{"gap_key": k[0], "gap_label": k[1], "patients": int(v)} for k, v in g.items()]


def statin_gap_panel(limit: int = 15) -> dict:
    s = summary()
    gap = s[s["open_care_gaps"].str.contains("statin_gap", na=False)]
    cols = ["patient_id", "full_name", "age", "cv_risk_band", "ascvd_10yr_pct",
            "ldl_latest", "established_cvd", "facility_name"]
    return {"total": int(len(gap)),
            "by_band": groupby_aggregate("cv_risk_band",
                                         filters=[{"column": "open_care_gaps", "op": "contains", "value": "statin_gap"}])["rows"],
            "patients": gap.sort_values("ascvd_10yr_pct", ascending=False)
                           .head(limit)[cols].replace({np.nan: None}).to_dict("records")}


def monthly_visits() -> list[dict]:
    enc = tables()["encounters"]
    amb = enc[enc["encounter_type"].isin(["outpatient", "telehealth"])].copy()
    amb["month"] = amb["start_date"].str[:7]
    g = amb.groupby("month").size()
    return [{"month": m, "visits": int(v)} for m, v in g.items()][:-1]


def cost_concentration() -> dict:
    s = summary().sort_values("annual_cost_qar", ascending=False).reset_index(drop=True)
    total = s["annual_cost_qar"].sum()
    cum = s["annual_cost_qar"].cumsum() / total * 100
    deciles = []
    n = len(s)
    for d in range(1, 11):
        idx = int(n * d / 10) - 1
        deciles.append({"top_pct_patients": d * 10, "pct_of_spend": round(float(cum[idx]), 1)})
    top10_share = round(float(cum[int(n * 0.1) - 1]), 1)
    return {"total_annual_cost_qar": int(total), "top10pct_share_pct": top10_share,
            "deciles": deciles}


def quality_measures() -> list[dict]:
    """HEDIS-style quality measures computed live from the HIE. Shared with the MCP server."""
    s = summary()
    dm = s[s["diabetes_type"] != "none"]
    hr = s[s["cv_risk_band"].isin(["High", "Very High"])]
    htn = s[s["htn"] == 1]
    af = s[s["af"] == 1]
    hfr = s[(s["hf"] == 1) & (s["ef_latest"].notna()) & (s["ef_latest"] < 40)]

    def m(mid, name, num, den, target, higher_is_better=True):
        num, den = int(num), int(den)
        rate = round(num / den * 100, 1) if den else 0.0
        return {"measure_id": mid, "name": name, "numerator": num, "denominator": den,
                "rate_pct": rate, "target_pct": target,
                "met": bool(rate >= target) if higher_is_better else bool(rate <= target),
                "gap_patients": (den - num) if higher_is_better else num}

    return [
        m("NABD-DM-01", "HbA1c testing in last 6 months (diabetes)",
          (dm["hba1c_days_since_test"] <= 183).sum(), len(dm), 90),
        m("NABD-DM-02", "Glycaemic control HbA1c <8% (diabetes)",
          (dm["hba1c_latest"] < 8).sum(), len(dm), 70),
        m("NABD-DM-03", "Urine ACR screening in last 12 months (diabetes)",
          dm["acr_latest"].notna().sum(), len(dm), 80),
        m("NABD-CV-01", "Statin therapy — high/very-high CV risk",
          (hr["on_statin"] == 1).sum(), len(hr), 85),
        m("NABD-CV-02", "BP controlled <140/90 (hypertension)",
          (htn["bp_controlled"] == 1).sum(), len(htn), 65),
        m("NABD-CV-03", "LDL at guideline target",
          (s["ldl_at_target"] == 1).sum(), s["ldl_at_target"].notna().sum(), 60),
        m("NABD-CV-04", "Anticoagulation in atrial fibrillation",
          (af["on_anticoagulant"] == 1).sum(), len(af), 90),
        m("NABD-CV-05", "HFrEF on beta-blocker + RAAS inhibitor",
          ((hfr["on_beta_blocker"] == 1) & (hfr["on_raas_inhibitor"] == 1)).sum(), len(hfr), 80),
    ]
