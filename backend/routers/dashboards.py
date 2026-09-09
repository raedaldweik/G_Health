"""Dashboard APIs — every number comes from the same services the agent uses."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter

from services import hie, ml

router = APIRouter()


@router.get("/api/dashboards/overview")
def overview():
    kpi = hie.cohort_stats()
    fc = ml.visit_forecast()
    s_ = hie.summary()
    return {
        "kpis": [
            {"label": "Patients in the registry", "value": f"{kpi['patients']:,}"},
            {"label": "Mean HbA1c", "value": kpi["mean_hba1c"], "suffix": "%"},
            {"label": "Well-controlled (<7%)", "value": kpi["pct_well_controlled"], "suffix": "%"},
            {"label": "Poorly controlled (≥9%)", "value": kpi["pct_poorly_controlled"], "suffix": "%"},
            {"label": "HbA1c overdue", "value": kpi["hba1c_overdue_patients"], "accent": "red"},
            {"label": "Annual cost", "value": f"{kpi['total_annual_cost_qar']/1e6:.1f}", "suffix": "M QAR"},
        ],
        "hba1c_trend": hie.hba1c_trend_monthly(),
        "visits": {"history": fc["history"], "forecast": fc["forecast"],
                   "yoy_growth_pct": fc["yoy_growth_pct"]},
        "facility_benchmark": hie.facility_benchmark(),
        "risk_distribution": hie.risk_tier_distribution(),
        "care_gaps": hie.care_gap_summary(),
        "complication_prevalence": hie.complication_prevalence(),
        "therapy_mix": [{"therapy": k, "pct": v} for k, v in
                        [("Metformin", round(float(s_["on_metformin"].mean()) * 100, 1)),
                         ("SGLT2i / GLP-1 RA", kpi["pct_on_sglt2_glp1"]), ("Insulin", kpi["pct_on_insulin"]),
                         ("RAAS inhibitor", round(float(s_["on_raas_inhibitor"].mean()) * 100, 1))]],
    }


@router.get("/api/dashboards/clinical")
def clinical():
    s = hie.summary()
    dm = s
    bands = pd.cut(dm["hba1c_latest"], [0, 7, 8, 9, 20],
                   labels=["<7% (target)", "7–8%", "8–9%", ">9% (poor control)"])
    control_dist = [{"band": str(b), "patients": int(n)}
                    for b, n in bands.value_counts().sort_index().items()]
    htn = s[s["htn"] == 1]
    gaps = tables_gap_matrix()
    return {
        "quality_measures": hie.quality_measures(),
        "control_distribution": control_dist,
        "bp_control": {"controlled": int((htn["bp_controlled"] == 1).sum()),
                       "uncontrolled": int((htn["bp_controlled"] == 0).sum())},
        "screening": {"retinal_pct": round(float((s["retinal_screening_overdue"] == 0).mean()) * 100, 1),
                      "foot_pct": round(float((s["foot_exam_overdue"] == 0).mean()) * 100, 1),
                      "acr_pct": round(float(s["acr_latest"].notna().mean()) * 100, 1)},
        "care_gaps": hie.care_gap_summary(),
        "gap_facility_matrix": gaps,
        "hba1c_trend": hie.hba1c_trend_monthly(),
    }


def tables_gap_matrix():
    g = hie.tables()["care_gaps"].merge(
        hie.tables()["facilities"][["facility_id", "facility_name"]], on="facility_id")
    top_gaps = g["gap_key"].value_counts().head(5).index.tolist()
    m = (g[g["gap_key"].isin(top_gaps)]
         .groupby(["facility_name", "gap_key"]).size().unstack(fill_value=0))
    return {"gap_keys": top_gaps,
            "rows": [{"facility": idx, **{k: int(v) for k, v in row.items()}}
                     for idx, row in m.iterrows()]}


@router.get("/api/dashboards/risk")
def risk():
    strat = ml.stratify_cohort(top_n=8)
    cards = ml.model_cards()
    risk_card = next(c for c in cards if c["model_id"] == "complication_risk")
    return {
        "model_cards": cards,
        "band_distribution": strat["model_band_distribution"],
        "expected_events_12m": strat["expected_events_12m"],
        "highest_risk": strat["highest_risk_patients"],
        "top_drivers": risk_card["metrics"]["top_drivers"],
        "calibration": risk_card["metrics"]["calibration_deciles"],
        "auc": risk_card["metrics"]["auc"],
        "legacy_auc": risk_card["metrics"]["legacy_score_auc"],
        "segments": ml.segment_summary(),
        "risk_profiles": hie.risk_profiles(),
    }


@router.get("/api/dashboards/cost")
def cost():
    s = hie.summary()
    by_fac = (s.groupby("facility_name")["annual_cost_qar"].agg(["sum", "mean", "count"])
              .round(0).sort_values("sum", ascending=False).reset_index())
    scatter = s.sample(500, random_state=3)[
        ["hba1c_latest", "annual_cost_qar", "registry_risk_tier"]].round(1)
    return {
        "concentration": hie.cost_concentration(),
        "segments": ml.segment_summary()["segments"],
        "by_facility": [{"facility": r["facility_name"],
                         "total_qar_m": round(r["sum"] / 1e6, 2),
                         "mean_qar": int(r["mean"]), "patients": int(r["count"])}
                        for _, r in by_fac.iterrows()],
        "equity": hie.equity_breakdown(),
        "risk_cost_scatter": scatter.to_dict("records"),
    }


@router.get("/api/dashboards/map")
def geography():
    from services import geo
    return geo.map_payload()
