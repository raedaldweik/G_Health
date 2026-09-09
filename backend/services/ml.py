"""
Nabd — ML scoring service.

Loads the trained artifacts (see scripts/train_models.py) and serves:
  • real-time patient risk scoring with per-feature SHAP explanations
    (XGBoost pred_contribs — no external explainability dependency),
  • cohort-level risk stratification,
  • patient similarity lookups,
  • population segments,
  • the ambulatory demand forecast,
  • the counterfactual policy simulator: flip treatment flags on the eligible
    cohort, re-score through the SAME deployed model, aggregate the predicted
    event reduction and cost impact. This is a real what-if, not a canned number.

Phase 2: the identical scoring call moves to a Vertex AI online endpoint hit
through the official Agent Platform /mcp/predict MCP toolset.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from xgboost import Booster, DMatrix

from services import hie

MODELS = Path(__file__).resolve().parent.parent / "models"

# Cost assumptions for the simulator (documented, deliberately conservative)
EVENT_COST_QAR = 18500          # average diabetes deterioration episode (admission + follow-up)
INTERVENTION_COSTS = {          # annual programme cost per patient (from the HIE med table + programme design)
    "sglt2_glp1_intensification": 6400,   # blended SGLT2i / GLP-1 RA therapy cost
    "hba1c_recall_program": 350,          # recall call + test + nurse review
    "adherence_support_program": 1200,    # pharmacist-led adherence coaching
    "bp_control_program": 900,            # titration visits + one added agent
    "renal_protection_program": 480,      # RAAS inhibitor + monitoring
}


@lru_cache(maxsize=1)
def _risk():
    booster = Booster()
    booster.load_model(str(MODELS / "complication_risk.xgb.json"))
    spec = json.loads((MODELS / "complication_risk.features.json").read_text())
    return booster, spec["features"], spec["intervenable"]


@lru_cache(maxsize=1)
def _similarity():
    return joblib.load(MODELS / "patient_similarity.joblib")


@lru_cache(maxsize=1)
def _segments():
    return joblib.load(MODELS / "cohort_segments.joblib")


@lru_cache(maxsize=1)
def model_cards() -> list[dict]:
    return json.loads((MODELS / "model_cards.json").read_text())


def _feature_frame(rows: pd.DataFrame) -> pd.DataFrame:
    df = rows.copy()
    df["is_male"] = (df["gender"] == "male").astype(int)
    _, features, _ = _risk()
    return df[features]


def _score(X: pd.DataFrame) -> np.ndarray:
    booster, _, _ = _risk()
    return booster.predict(DMatrix(X))


def _band(p: float) -> str:
    return "Very High" if p >= 0.25 else "High" if p >= 0.12 else "Moderate" if p >= 0.05 else "Low"


def score_patient(patient_id: str) -> dict:
    s = hie.summary()
    row = s[s["patient_id"] == patient_id]
    if row.empty:
        return {"error": f"patient {patient_id} not found"}
    if row.iloc[0]["consent_status"] == "restricted":
        return {"consent": "DENIED", "message": "Restricted consent — scoring blocked and logged."}
    X = _feature_frame(row)
    booster, features, _ = _risk()
    prob = float(_score(X)[0])
    contribs = booster.predict(DMatrix(X), pred_contribs=True)[0]
    pairs = sorted(zip(features + ["baseline"], contribs), key=lambda t: -abs(t[1]))
    drivers = [{"feature": f, "value": (None if f == "baseline" else
                                        (None if pd.isna(X.iloc[0].get(f)) else float(X.iloc[0].get(f)))),
                "contribution": round(float(c), 4)}
               for f, c in pairs if f != "baseline"][:8]
    return {"patient_id": patient_id, "model": "deterioration_risk v2.1.0",
            "event_probability_12m": round(prob, 4), "risk_band_model": _band(prob),
            "registry_tier": row.iloc[0]["registry_risk_tier"],
            "top_drivers": drivers,
            "note": "SHAP-style contributions from XGBoost pred_contribs; positive pushes risk up."}


def stratify_cohort(filters: list[dict] | None = None, top_n: int = 10) -> dict:
    df = hie._apply_filters(hie.summary(), filters)
    df = df[df["consent_status"] != "restricted"]
    if df.empty:
        return {"matched": 0}
    probs = _score(_feature_frame(df))
    df = df.assign(risk_prob=probs)
    dist = {b: int((df["risk_prob"].apply(_band) == b).sum())
            for b in ["Low", "Moderate", "High", "Very High"]}
    top = (df.sort_values("risk_prob", ascending=False)
           .head(top_n)[["patient_id", "full_name", "age", "facility_name",
                         "hba1c_latest", "registry_risk_tier", "care_gap_count", "risk_prob"]])
    top["risk_prob"] = top["risk_prob"].round(4)
    return {"matched": int(len(df)),
            "mean_event_probability": round(float(df["risk_prob"].mean()), 4),
            "expected_events_12m": round(float(df["risk_prob"].sum()), 1),
            "model_band_distribution": dist,
            "highest_risk_patients": top.replace({np.nan: None}).to_dict("records")}


def similar_patients(patient_id: str, k: int = 6) -> dict:
    art = _similarity()
    ids = art["patient_ids"]
    if patient_id not in ids:
        return {"error": f"patient {patient_id} not found"}
    s = hie.summary().set_index("patient_id")
    feats = s.loc[ids, art["features"]].fillna(s[art["features"]].median())
    idx = ids.index(patient_id)
    X = art["scaler"].transform(feats)
    dist, nbr = art["nn"].kneighbors(X[idx:idx + 1], n_neighbors=k + 1)
    out = []
    for d, i in zip(dist[0][1:], nbr[0][1:]):
        pid = ids[i]
        r = s.loc[pid]
        if r["consent_status"] == "restricted":
            continue
        out.append({"patient_id": pid, "distance": round(float(d), 2), "age": int(r["age"]),
                    "hba1c_latest": None if pd.isna(r["hba1c_latest"]) else float(r["hba1c_latest"]),
                    "registry_risk_tier": r["registry_risk_tier"], "on_insulin": int(r["on_insulin"]),
                    "on_sglt2_glp1": int(r["on_sglt2_glp1"]), "adherence_pdc": float(r["adherence_pdc"]),
                    "glycaemic_control": r["glycaemic_control"],
                    "annual_cost_qar": float(r["annual_cost_qar"])})
    return {"patient_id": patient_id, "similar": out,
            "note": "Nearest neighbours in standardised clinical feature space."}


def segment_summary() -> dict:
    art = _segments()
    s = hie.summary()
    probs = _score(_feature_frame(s))
    feats = pd.DataFrame({"annual_cost_qar": s["annual_cost_qar"], "risk_prob": probs,
                          "age": s["age"], "care_gap_count": s["care_gap_count"],
                          "admissions_12mo": s["admissions_12mo"]})[art["features"]]
    labels = art["kmeans"].predict(art["scaler"].transform(feats))
    s2 = s.assign(segment=[art["segment_names"][int(l)] for l in labels],
                  risk_prob=probs)
    g = s2.groupby("segment").agg(
        patients=("patient_id", "count"), mean_cost=("annual_cost_qar", "mean"),
        total_cost=("annual_cost_qar", "sum"), mean_risk=("risk_prob", "mean"),
        mean_gaps=("care_gap_count", "mean"), mean_age=("age", "mean")).round(2)
    return {"segments": [{"segment": k, **{c: (v.item() if hasattr(v, "item") else v)
                                           for c, v in row.items()}}
                         for k, row in g.iterrows()],
            "scatter_sample": s2.sample(600, random_state=1)[
                ["risk_prob", "annual_cost_qar", "segment"]].round(4).to_dict("records")}


def visit_forecast() -> dict:
    return json.loads((MODELS / "visit_forecast.json").read_text())


# ─────────────────────────── counterfactual policy simulator ───────────────────────────

INTERVENTIONS = {
    "sglt2_glp1_intensification": {
        "label": "Treatment intensification: SGLT2i / GLP-1 RA in uncontrolled T2DM with obesity or CKD",
        "eligible": lambda s: (s["diabetes_type"] == "type2") & (s["on_sglt2_glp1"] == 0)
                              & (s["hba1c_latest"] >= 8)
                              & ((s["bmi"] >= 30) | (s["ckd"] == 1) | (s["albuminuria"] == 1)),
        "apply": {"on_sglt2_glp1": 1},
    },
    "hba1c_recall_program": {
        "label": "HbA1c recall programme: bring every overdue patient back for testing and review",
        "eligible": lambda s: s["hba1c_days_since_test"].fillna(9999) > 183,
        "apply": {"hba1c_days_since_test": 60},
    },
    "adherence_support_program": {
        "label": "Pharmacist-led adherence support for patients below 60% PDC",
        "eligible": lambda s: s["adherence_pdc"] < 0.6,
        "apply": {"adherence_pdc": 0.85},
    },
    "bp_control_program": {
        "label": "Blood-pressure control programme (titrate uncontrolled BP in diabetes)",
        "eligible": lambda s: (s["htn"] == 1) & (s["bp_controlled"] == 0),
        "apply": "bp",   # special: lower sbp/dbp to guideline-adjacent values
    },
    "renal_protection_program": {
        "label": "Renal protection: RAAS inhibitor for CKD or albuminuria",
        "eligible": lambda s: ((s["ckd"] == 1) | (s["albuminuria"] == 1)) & (s["on_raas_inhibitor"] == 0),
        "apply": {"on_raas_inhibitor": 1},
    },
}


def simulate_policy(intervention: str, horizon_months: int = 12) -> dict:
    """Counterfactual what-if: flip the treatment for the eligible cohort and re-score
    every patient through the SAME risk model. No canned numbers."""
    if intervention == "combined":
        parts = [simulate_policy(k, horizon_months) for k in INTERVENTIONS]
        return {"intervention": "combined", "label": "All five programmes combined",
                "horizon_months": horizon_months,
                "components": parts,
                "eligible_patients": sum(p["eligible_patients"] for p in parts),
                "expected_events_avoided": round(sum(p["expected_events_avoided"] for p in parts), 1),
                "event_cost_avoided_qar": int(sum(p["event_cost_avoided_qar"] for p in parts)),
                "programme_cost_qar": int(sum(p["programme_cost_qar"] for p in parts)),
                "net_benefit_qar": int(sum(p["net_benefit_qar"] for p in parts)),
                "method": parts[0]["method"]}

    spec = INTERVENTIONS.get(intervention)
    if not spec:
        return {"error": f"unknown intervention '{intervention}'",
                "available": list(INTERVENTIONS) + ["combined"]}
    s = hie.summary()
    s = s[s["consent_status"] != "restricted"]
    mask = spec["eligible"](s).fillna(False)
    cohort = s[mask]
    if cohort.empty:
        return {"intervention": intervention, "eligible_patients": 0}

    X0 = _feature_frame(cohort)
    p0 = _score(X0)
    cf = cohort.copy()
    if spec["apply"] == "bp":
        cf["sbp_latest"] = np.maximum(cf["sbp_latest"] - 14, 126)
        cf["dbp_latest"] = np.maximum(cf["dbp_latest"] - 7, 76)
    else:
        for col, val in spec["apply"].items():
            cf[col] = val
    p1 = _score(_feature_frame(cf))

    scale = horizon_months / 12
    events_avoided = float((p0 - p1).sum()) * scale
    rel = float(1 - (p1.mean() / p0.mean())) * 100
    programme = int(len(cohort) * INTERVENTION_COSTS[intervention] * scale)
    avoided_cost = int(events_avoided * EVENT_COST_QAR)
    return {
        "intervention": intervention, "label": spec["label"],
        "horizon_months": horizon_months, "eligible_patients": int(len(cohort)),
        "mean_risk_before": round(float(p0.mean()), 4),
        "mean_risk_after": round(float(p1.mean()), 4),
        "relative_risk_reduction_pct": round(rel, 1),
        "expected_events_avoided": round(events_avoided, 1),
        "event_cost_avoided_qar": avoided_cost,
        "programme_cost_qar": programme,
        "net_benefit_qar": avoided_cost - programme,
        "method": ("Counterfactual re-scoring: the eligible cohort is re-scored through the "
                   "deterioration-risk XGBoost model with the programme applied; the "
                   f"event delta is costed at QAR {EVENT_COST_QAR:,} per avoided deterioration episode."),
    }
