"""Dashboard APIs. Every number comes from the same services the agent uses, and every
endpoint accepts the dashboard cross-filter (`filters`, a JSON object such as
{"tier": "High"} or {"facility": "Al Wakra Hospital"}): a click on any bar, slice or row
in the UI narrows the patient frame, and every panel is recomputed from that frame."""
from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, HTTPException

from services import hie, ml

router = APIRouter()


def _filters(raw: str) -> dict:
    if not raw:
        return {}
    try:
        f = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(400, "filters must be a JSON object")
    return {k: v for k, v in (f or {}).items() if k in hie.FILTER_LABELS and v not in (None, "")}


def _frame(raw: str):
    f = _filters(raw)
    df = hie.filtered_summary(f)
    info = {"active": f, "chips": hie.describe_filters(f), "patients": int(len(df)),
            "total": int(len(hie.summary()))}
    return df, info


@router.get("/api/dashboards/overview")
def overview(filters: str = ""):
    df, info = _frame(filters)
    kpi = hie.cohort_stats(df)
    fc = ml.visit_forecast()
    n = max(len(df), 1)
    return {
        "filter": info,
        "kpis": [
            {"label": "Patients" + (" in the filter" if info["active"] else " in the registry"), "value": f"{kpi['patients']:,}"},
            {"label": "Mean HbA1c", "value": kpi["mean_hba1c"], "suffix": "%"},
            {"label": "Well-controlled (<7%)", "value": kpi["pct_well_controlled"], "suffix": "%"},
            {"label": "Poorly controlled (≥9%)", "value": kpi["pct_poorly_controlled"], "suffix": "%"},
            {"label": "HbA1c overdue", "value": kpi["hba1c_overdue_patients"], "accent": "red"},
            {"label": "Annual cost", "value": f"{kpi['total_annual_cost_qar']/1e6:.1f}", "suffix": "M QAR"},
        ],
        "hba1c_trend": hie.hba1c_trend_monthly(df if info["active"] else None),
        "visits": {"history": fc["history"], "forecast": fc["forecast"],
                   "yoy_growth_pct": fc["yoy_growth_pct"]},
        "facility_benchmark": hie.facility_benchmark(df),
        "risk_distribution": hie.risk_tier_distribution(df),
        "care_gaps": hie.care_gap_summary(df),
        "complication_prevalence": hie.complication_prevalence(df),
        "therapy_mix": [{"therapy": k, "pct": v} for k, v in
                        [("Metformin", round(float(df["on_metformin"].mean()) * 100, 1) if len(df) else 0.0),
                         ("SGLT2i / GLP-1 RA", kpi["pct_on_sglt2_glp1"]), ("Insulin", kpi["pct_on_insulin"]),
                         ("RAAS inhibitor", round(float(df["on_raas_inhibitor"].mean()) * 100, 1) if len(df) else 0.0)]],
    }


@router.get("/api/dashboards/clinical")
def clinical(filters: str = ""):
    s, info = _frame(filters)
    bands = pd.cut(s["hba1c_latest"], [0, 7, 8, 9, 100], right=False,
                   labels=[b[0] for b in hie.HBA1C_BANDS])
    control_dist = [{"band": str(b), "patients": int(n)}
                    for b, n in bands.value_counts().sort_index().items()]
    htn = s[s["htn"] == 1]
    return {
        "filter": info,
        "quality_measures": hie.quality_measures(s),
        "control_distribution": control_dist,
        "bp_control": {"controlled": int((htn["bp_controlled"] == 1).sum()),
                       "uncontrolled": int((htn["bp_controlled"] == 0).sum())},
        "screening": {"retinal_pct": round(float((s["retinal_screening_overdue"] == 0).mean()) * 100, 1) if len(s) else 0.0,
                      "foot_pct": round(float((s["foot_exam_overdue"] == 0).mean()) * 100, 1) if len(s) else 0.0,
                      "acr_pct": round(float(s["acr_latest"].notna().mean()) * 100, 1) if len(s) else 0.0},
        "care_gaps": hie.care_gap_summary(s),
        "gap_facility_matrix": tables_gap_matrix(s),
        "hba1c_trend": hie.hba1c_trend_monthly(s if info["active"] else None),
    }


def tables_gap_matrix(df=None):
    g = hie.tables()["care_gaps"].merge(
        hie.tables()["facilities"][["facility_id", "facility_name"]], on="facility_id")
    if df is not None:
        g = g[g["patient_id"].isin(df["patient_id"])]
    top_gaps = g["gap_key"].value_counts().head(5).index.tolist()
    m = (g[g["gap_key"].isin(top_gaps)]
         .groupby(["facility_name", "gap_key"]).size().unstack(fill_value=0))
    return {"gap_keys": top_gaps,
            "rows": [{"facility": idx, **{k: int(v) for k, v in row.items()}}
                     for idx, row in m.iterrows()]}


@router.get("/api/dashboards/risk")
def risk(filters: str = ""):
    df, info = _frame(filters)
    strat = ml.stratify_cohort(top_n=8, df=df)
    cards = ml.model_cards()
    risk_card = next(c for c in cards if c["model_id"] == "complication_risk")
    return {
        "filter": info,
        "model_cards": cards,
        "band_distribution": strat.get("model_band_distribution", {}),
        "expected_events_12m": strat.get("expected_events_12m", 0),
        "highest_risk": strat.get("highest_risk_patients", []),
        "top_drivers": risk_card["metrics"]["top_drivers"],
        "calibration": risk_card["metrics"]["calibration_deciles"],
        "auc": risk_card["metrics"]["auc"],
        "legacy_auc": risk_card["metrics"]["legacy_score_auc"],
        "segments": ml.segment_summary(df),
        "risk_profiles": hie.risk_profiles(df),
    }


@router.get("/api/dashboards/cost")
def cost(filters: str = ""):
    s, info = _frame(filters)
    by_fac = (s.groupby("facility_name")["annual_cost_qar"].agg(["sum", "mean", "count"])
              .round(0).sort_values("sum", ascending=False).reset_index())
    scatter = s.sample(min(500, len(s)), random_state=3)[
        ["hba1c_latest", "annual_cost_qar", "registry_risk_tier"]].round(1)
    return {
        "filter": info,
        "concentration": hie.cost_concentration(s),
        "segments": ml.segment_summary(s)["segments"],
        "by_facility": [{"facility": r["facility_name"],
                         "total_qar_m": round(r["sum"] / 1e6, 2),
                         "mean_qar": int(r["mean"]), "patients": int(r["count"])}
                        for _, r in by_fac.iterrows()],
        "equity": hie.equity_breakdown(s),
        "risk_cost_scatter": scatter.to_dict("records"),
    }


@router.get("/api/dashboards/map")
def geography():
    from services import geo
    return geo.map_payload()
