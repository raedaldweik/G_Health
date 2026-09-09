"""
Nabd, HIE query engine.

Loads the synthetic Health Information Exchange (8 relational tables) once and
exposes the structured query surface used by BOTH the agent tools and the
dashboard APIs, one source of truth, so the chat and the dashboards can never
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
    "bp_uncontrolled": "Blood pressure uncontrolled (≥140/90)",
    "glp1_sglt2_gap": "T2DM ≥8% with obesity/CKD not on SGLT2i or GLP-1 RA",
    "therapy_inertia": "HbA1c ≥9% with no treatment intensification",
    "low_adherence": "Medication adherence below 60% (PDC)",
    "renal_protection_gap": "CKD or albuminuria without RAAS inhibitor",
}
TIER_ORDER = ["Low", "Moderate", "High", "Very High"]

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
            print(f"⚠ BigQuery unavailable ({bq.STATUS['error']}), serving the local HIE files"
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
        "note": ("patient_summary is the wide analytical table, use it for cohort filters, "
                 "group-bys and rankings. observations holds the longitudinal labs/vitals "
                 "(obs_key ∈ hba1c,fpg,sbp,dbp,ldl,hdl,tg,egfr,acr,bmi). Every patient in the "
                 "registry has diabetes (diabetes_type = type1 | type2)."),
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
                "message": ("Patient consent status is RESTRICTED, record access blocked "
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
            raise ValueError(f"unknown column '{col}', call describe_dataset for the schema")
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

# ── Dashboard cross-filtering ─────────────────────────────────────────────────────────
HBA1C_BANDS = [("<7% (target)", 0, 7), ("7–8%", 7, 8), ("8–9%", 8, 9), (">9% (poor control)", 9, 100)]
FILTER_LABELS = {"tier": "Registry tier", "facility": "Facility", "nationality": "Nationality",
                 "diabetes_type": "Diabetes type", "hba1c_band": "HbA1c band", "gap": "Care gap",
                 "condition": "Condition", "bp": "BP control", "segment": "Segment", "model_band": "Model band"}


def _condition_masks(s: pd.DataFrame) -> dict:
    return {"Hypertension": s["htn"] == 1, "Dyslipidaemia": s["dyslipidemia"] == 1,
            "Obesity (BMI ≥30)": s["bmi"] >= 30, "Diabetic retinopathy": s["retinopathy"] == 1,
            "Diabetic neuropathy": s["neuropathy"] == 1, "Chronic kidney disease": s["ckd"] == 1,
            "Albuminuria": s["albuminuria"] == 1, "Foot ulcer history": s["foot_ulcer_history"] == 1}


def filtered_summary(filters: dict | None) -> pd.DataFrame:
    """Apply the dashboard cross-filter (clicked bars, chips) to the patient summary.
    Every dashboard panel is then recomputed from the same filtered frame."""
    s = summary()
    for k, v in (filters or {}).items():
        if v in (None, "", []):
            continue
        if k == "tier":
            s = s[s["registry_risk_tier"] == v]
        elif k == "facility":
            s = s[s["facility_name"] == v]
        elif k == "nationality":
            s = s[s["nationality"] == v]
        elif k == "diabetes_type":
            s = s[s["diabetes_type"] == v]
        elif k == "hba1c_band":
            band = next((b for b in HBA1C_BANDS if b[0] == v), None)
            if band:
                s = s[(s["hba1c_latest"] >= band[1]) & (s["hba1c_latest"] < band[2])]
        elif k == "gap":
            s = s[s["open_care_gaps"].str.contains(v, na=False)]
        elif k == "condition":
            m = _condition_masks(s).get(v)
            if m is not None:
                s = s[m]
        elif k == "bp":
            s = s[(s["htn"] == 1) & (s["bp_controlled"] == (1 if v == "Controlled" else 0))]
        elif k == "segment":
            from services import ml
            s = s[ml.segment_labels(s) == v]
        elif k == "model_band":
            from services import ml
            probs = ml._score(ml._feature_frame(s))
            s = s[[ml._band(float(x)) == v for x in probs]]
    return s


def describe_filters(filters: dict | None) -> list[dict]:
    return [{"key": k, "label": FILTER_LABELS.get(k, k), "value": v}
            for k, v in (filters or {}).items() if v not in (None, "", [])]


def cohort_stats(df: pd.DataFrame | None = None) -> dict:
    s = summary() if df is None else df
    if s.empty:
        return {"patients": 0, "with_diabetes": 0, "pct_type1": 0.0, "mean_hba1c": 0.0, "pct_well_controlled": 0.0,
                "pct_uncontrolled": 0.0, "pct_poorly_controlled": 0.0, "pct_retinopathy": 0.0, "pct_neuropathy": 0.0,
                "pct_ckd": 0.0, "pct_on_sglt2_glp1": 0.0, "pct_on_insulin": 0.0, "mean_adherence_pdc": 0.0,
                "hba1c_overdue_patients": 0, "retinal_overdue_patients": 0, "foot_exam_overdue_patients": 0,
                "intensification_gap_patients": 0, "therapy_inertia_patients": 0, "low_adherence_patients": 0,
                "renal_protection_gap_patients": 0, "bp_uncontrolled_patients": 0, "total_open_care_gaps": 0,
                "total_annual_cost_qar": 0, "admissions_12mo": 0, "ed_visits_12mo": 0}
    dm = s
    gc = lambda k: int(s["open_care_gaps"].str.contains(k, na=False).sum())
    return {
        "patients": len(s), "with_diabetes": len(dm),
        "pct_type1": round(float((s["diabetes_type"] == "type1").mean()) * 100, 1),
        "mean_hba1c": round(float(dm["hba1c_latest"].mean()), 2),
        "pct_well_controlled": round(float((dm["glycaemic_control"] == "well_controlled").mean()) * 100, 1),
        "pct_uncontrolled": round(float(dm["glycaemic_control"].isin(["uncontrolled", "poorly_controlled"]).mean()) * 100, 1),
        "pct_poorly_controlled": round(float((dm["hba1c_latest"] >= 9).mean()) * 100, 1),
        "pct_retinopathy": round(float(s["retinopathy"].mean()) * 100, 1),
        "pct_neuropathy": round(float(s["neuropathy"].mean()) * 100, 1),
        "pct_ckd": round(float(s["ckd"].mean()) * 100, 1),
        "pct_on_sglt2_glp1": round(float(s["on_sglt2_glp1"].mean()) * 100, 1),
        "pct_on_insulin": round(float(s["on_insulin"].mean()) * 100, 1),
        "mean_adherence_pdc": round(float(s["adherence_pdc"].mean()), 2),
        "hba1c_overdue_patients": gc("hba1c_overdue"),
        "retinal_overdue_patients": gc("retinal_screening_overdue"),
        "foot_exam_overdue_patients": gc("foot_exam_overdue"),
        "intensification_gap_patients": gc("glp1_sglt2_gap"),
        "therapy_inertia_patients": gc("therapy_inertia"),
        "low_adherence_patients": gc("low_adherence"),
        "renal_protection_gap_patients": gc("renal_protection_gap"),
        "bp_uncontrolled_patients": gc("bp_uncontrolled"),
        "total_open_care_gaps": int(s["care_gap_count"].sum()),
        "total_annual_cost_qar": int(s["annual_cost_qar"].sum()),
        "admissions_12mo": int(s["admissions_12mo"].sum()),
        "ed_visits_12mo": int(s["ed_visits_12mo"].sum()),
    }


def hba1c_trend_monthly(df: pd.DataFrame | None = None) -> list[dict]:
    obs = tables()["observations"]
    h = obs[obs["obs_key"] == "hba1c"].copy()
    min_n = 30
    if df is not None:
        h = h[h["patient_id"].isin(df["patient_id"])]
        min_n = max(4, round(30 * len(df) / max(len(summary()), 1)))
    h["month"] = h["effective_date"].str[:7]
    g = h.groupby("month")["value"].agg(["mean", "count"])
    g = g[g["count"] >= min_n]
    return [{"month": m, "mean_hba1c": round(float(r["mean"]), 2), "tests": int(r["count"])}
            for m, r in g.iterrows()]


def facility_benchmark(df: pd.DataFrame | None = None) -> list[dict]:
    s = summary() if df is None else df
    if s.empty:
        return []
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


def equity_breakdown(df: pd.DataFrame | None = None) -> list[dict]:
    s = summary() if df is None else df
    if s.empty:
        return []
    dm = s[s["diabetes_type"] != "none"]
    g = dm.groupby("nationality").agg(
        patients=("patient_id", "count"),
        mean_hba1c=("hba1c_latest", "mean"),
        pct_controlled=("glycaemic_control", lambda x: (x == "well_controlled").mean() * 100),
        mean_gaps=("care_gap_count", "mean"),
        mean_cost=("annual_cost_qar", "mean"),
    ).round(2).reset_index().sort_values("mean_hba1c", ascending=False)
    return g.to_dict("records")


def risk_tier_distribution(df: pd.DataFrame | None = None) -> list[dict]:
    """The registry's rule-based tiers (what clinicians see today, before the model)."""
    g = (summary() if df is None else df)["registry_risk_tier"].value_counts()
    return [{"band": b, "patients": int(g.get(b, 0))} for b in TIER_ORDER]


def complication_prevalence(df: pd.DataFrame | None = None) -> list[dict]:
    s = summary() if df is None else df
    return [{"condition": label, "patients": int(m.sum()),
             "prevalence_pct": round(float(m.mean()) * 100, 1) if len(s) else 0.0}
            for label, m in _condition_masks(s).items()]


def risk_profiles(df: pd.DataFrame | None = None) -> dict:
    """High-risk vs low-risk patient profile (top vs bottom model-risk decile): the
    diabetes programme's 'who deteriorates' view, computed from the exchange."""
    from services import ml
    s = summary() if df is None else df
    s = s[s["consent_status"] != "restricted"].copy()
    if len(s) < 20:
        return {"high_risk": None, "low_risk": None, "method": "Too few patients in the current filter for a decile profile."}
    s["risk_prob"] = ml._score(ml._feature_frame(s))
    hi = s[s["risk_prob"] >= s["risk_prob"].quantile(0.90)]
    lo = s[s["risk_prob"] <= s["risk_prob"].quantile(0.10)]

    def prof(g):
        nat = g["nationality"].value_counts(normalize=True).head(3)
        return {"patients": int(len(g)), "mean_risk_pct": round(float(g["risk_prob"].mean()) * 100, 1),
                "mean_age": round(float(g["age"].mean()), 0), "pct_male": round(float((g["gender"] == "male").mean()) * 100, 0),
                "mean_hba1c": round(float(g["hba1c_latest"].mean()), 1),
                "mean_years_since_dx": round(float(g["years_since_diagnosis"].mean()), 1),
                "mean_bmi": round(float(g["bmi"].mean()), 1),
                "mean_egfr": round(float(g["egfr_latest"].mean()), 0),
                "pct_retinopathy": round(float(g["retinopathy"].mean()) * 100, 0),
                "pct_neuropathy": round(float(g["neuropathy"].mean()) * 100, 0),
                "pct_ckd": round(float(g["ckd"].mean()) * 100, 0),
                "pct_on_insulin": round(float(g["on_insulin"].mean()) * 100, 0),
                "pct_on_sglt2_glp1": round(float(g["on_sglt2_glp1"].mean()) * 100, 0),
                "mean_adherence_pdc": round(float(g["adherence_pdc"].mean()), 2),
                "pct_hba1c_overdue": round(float((g["hba1c_days_since_test"].fillna(9999) > 183).mean()) * 100, 0),
                "mean_admissions_12mo": round(float(g["admissions_12mo"].mean()), 2),
                "mean_cost_qar": int(g["annual_cost_qar"].mean()),
                "top_nationalities": [{"nationality": k, "share_pct": round(float(v) * 100, 0)} for k, v in nat.items()]}
    return {"high_risk": prof(hi), "low_risk": prof(lo),
            "method": "Top vs bottom decile of the deterioration model's 12-month probability, consent-restricted patients excluded."}


def care_gap_summary(df: pd.DataFrame | None = None) -> list[dict]:
    gaps = tables()["care_gaps"]
    if df is not None:
        gaps = gaps[gaps["patient_id"].isin(df["patient_id"])]
    g = gaps.groupby(["gap_key", "gap_label"]).size().sort_values(ascending=False)
    return [{"gap_key": k[0], "gap_label": k[1], "patients": int(v)} for k, v in g.items()]


def gap_panel(gap_key: str = "glp1_sglt2_gap", limit: int = 15) -> dict:
    """Work list for one care gap, worst HbA1c first, with the registry-tier split."""
    s = summary()
    gap = s[s["open_care_gaps"].str.contains(gap_key, na=False)]
    cols = ["patient_id", "full_name", "age", "registry_risk_tier", "hba1c_latest",
            "hba1c_days_since_test", "bmi", "egfr_latest", "on_sglt2_glp1", "facility_name"]
    return {"gap_key": gap_key, "gap_label": GAP_LABELS.get(gap_key, gap_key), "total": int(len(gap)),
            "by_tier": groupby_aggregate("registry_risk_tier",
                                         filters=[{"column": "open_care_gaps", "op": "contains", "value": gap_key}])["rows"],
            "patients": gap.sort_values("hba1c_latest", ascending=False)
                           .head(limit)[cols].replace({np.nan: None}).to_dict("records")}


def monthly_visits() -> list[dict]:
    enc = tables()["encounters"]
    amb = enc[enc["encounter_type"].isin(["outpatient", "telehealth"])].copy()
    amb["month"] = amb["start_date"].str[:7]
    g = amb.groupby("month").size()
    return [{"month": m, "visits": int(v)} for m, v in g.items()][:-1]


def cost_concentration(df: pd.DataFrame | None = None) -> dict:
    s = (summary() if df is None else df).sort_values("annual_cost_qar", ascending=False).reset_index(drop=True)
    if s.empty:
        return {"total_annual_cost_qar": 0, "top10pct_share_pct": 0.0, "deciles": []}
    total = s["annual_cost_qar"].sum()
    cum = s["annual_cost_qar"].cumsum() / total * 100
    deciles = []
    n = len(s)
    for d in range(1, 11):
        idx = max(0, int(n * d / 10) - 1)
        deciles.append({"top_pct_patients": d * 10, "pct_of_spend": round(float(cum[idx]), 1)})
    top10_share = round(float(cum[max(0, int(n * 0.1) - 1)]), 1)
    return {"total_annual_cost_qar": int(total), "top10pct_share_pct": top10_share,
            "deciles": deciles}


def quality_measures(df: pd.DataFrame | None = None) -> list[dict]:
    """HEDIS-style quality measures computed live from the HIE. Shared with the MCP server."""
    s = summary() if df is None else df
    dm = s
    htn = s[s["htn"] == 1]
    t2_elig = s[(s["diabetes_type"] == "type2") & (s["hba1c_latest"] >= 8)
                & ((s["bmi"] >= 30) | (s["ckd"] == 1) | (s["albuminuria"] == 1))]
    renal = s[(s["ckd"] == 1) | (s["albuminuria"] == 1)]

    def m(mid, name, num, den, target, higher_is_better=True):
        num, den = int(num), int(den)
        rate = round(num / den * 100, 1) if den else 0.0
        return {"measure_id": mid, "name": name, "numerator": num, "denominator": den,
                "rate_pct": rate, "target_pct": target,
                "met": bool(rate >= target) if higher_is_better else bool(rate <= target),
                "gap_patients": (den - num) if higher_is_better else num}

    return [
        m("NABD-DM-01", "HbA1c tested in the last 6 months",
          (dm["hba1c_days_since_test"] <= 183).sum(), len(dm), 90),
        m("NABD-DM-02", "Glycaemic control, HbA1c <8%",
          (dm["hba1c_latest"] < 8).sum(), len(dm), 70),
        m("NABD-DM-03", "Poor control, HbA1c >9% (lower is better)",
          (dm["hba1c_latest"] > 9).sum(), len(dm), 15, higher_is_better=False),
        m("NABD-DM-04", "Retinal screening in the last 12 months",
          (dm["retinal_screening_overdue"] == 0).sum(), len(dm), 80),
        m("NABD-DM-05", "Diabetic foot exam in the last 12 months",
          (dm["foot_exam_overdue"] == 0).sum(), len(dm), 80),
        m("NABD-DM-06", "Urine ACR screening in the last 12 months",
          dm["acr_latest"].notna().sum(), len(dm), 80),
        m("NABD-DM-07", "BP controlled <140/90 (diabetes with hypertension)",
          (htn["bp_controlled"] == 1).sum(), len(htn), 65),
        m("NABD-DM-08", "SGLT2i / GLP-1 RA in eligible uncontrolled T2DM",
          (t2_elig["on_sglt2_glp1"] == 1).sum(), len(t2_elig), 60),
        m("NABD-DM-09", "RAAS inhibitor in CKD or albuminuria",
          (renal["on_raas_inhibitor"] == 1).sum(), len(renal), 80),
        m("NABD-DM-10", "Medication adherence ≥80% (PDC)",
          (dm["adherence_pdc"] >= 0.8).sum(), len(dm), 70),
    ]
