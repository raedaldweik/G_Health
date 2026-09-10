"""
Nabd, ML scoring service.

Loads the trained artifacts (see scripts/train_models.py) and serves:
  • real-time patient risk scoring with per-feature SHAP explanations
    (XGBoost pred_contribs, no external explainability dependency),
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
FEATURE_LABELS = {
    "age": "Age", "is_male": "Male sex", "bmi": "BMI", "bmi_change_12m": "BMI change (12 m)",
    "years_since_diagnosis": "Years since diagnosis", "smoker": "Smoking",
    "hba1c_latest": "HbA1c", "hba1c_12m_ago": "HbA1c 12 months ago", "hba1c_days_since_test": "Days since HbA1c test",
    "sbp_latest": "Systolic BP", "dbp_latest": "Diastolic BP", "egfr_latest": "eGFR", "acr_latest": "Urine ACR",
    "albuminuria": "Albuminuria", "retinopathy": "Retinopathy", "neuropathy": "Neuropathy",
    "foot_ulcer_history": "Foot ulcer history", "htn": "Hypertension", "on_metformin": "Metformin",
    "on_sglt2_glp1": "SGLT2i / GLP-1 RA", "on_insulin": "Insulin", "on_raas_inhibitor": "RAAS inhibitor",
    "adherence_pdc": "Adherence (PDC)", "admissions_12mo": "Admissions (12 m)", "ed_visits_12mo": "ED visits (12 m)",
    "diabetes_medication_count": "Diabetes medicines", "care_gap_count": "Open care gaps",
}
BAND_ORDER = ["Low", "Moderate", "High", "Very High"]
SCENARIO_DISCLAIMER = ("Predictive scenario analysis only. Changes in predicted risk are not estimates of "
                       "causal treatment effect or events prevented.")


@lru_cache(maxsize=1)
def _risk():
    booster = Booster()
    booster.load_model(str(MODELS / "complication_risk.xgb.json"))
    spec = json.loads((MODELS / "complication_risk.features.json").read_text())
    return booster, spec["features"], spec.get("sensitivity_inputs", spec.get("intervenable", []))


def model_version() -> str:
    try:
        return json.loads((MODELS / "complication_risk.features.json").read_text()).get("version", "2.2.0")
    except Exception:
        return "2.2.0"


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
        return {"consent": "DENIED", "message": "Restricted consent, scoring blocked and logged."}
    X = _feature_frame(row)
    booster, features, _ = _risk()
    prob = float(_score(X)[0])
    contribs = booster.predict(DMatrix(X), pred_contribs=True)[0]
    pairs = sorted(zip(features + ["baseline"], contribs), key=lambda t: -abs(t[1]))
    drivers = [{"feature": f, "value": (None if f == "baseline" else
                                        (None if pd.isna(X.iloc[0].get(f)) else float(X.iloc[0].get(f)))),
                "contribution": round(float(c), 4)}
               for f, c in pairs if f != "baseline"][:8]
    return {"patient_id": patient_id, "model": f"deterioration_risk v{model_version()}",
            "event_probability_12m": round(prob, 4), "risk_band_model": _band(prob),
            "registry_tier": row.iloc[0]["registry_risk_tier"],
            "top_drivers": drivers,
            "note": "SHAP-style contributions from XGBoost pred_contribs; positive pushes risk up."}


def stratify_cohort(filters: list[dict] | None = None, top_n: int = 10,
                    df: pd.DataFrame | None = None) -> dict:
    df = hie._apply_filters(hie.summary() if df is None else df, filters)
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


def segment_labels(s: pd.DataFrame) -> pd.Series:
    """KMeans segment name for every row of a patient-summary frame."""
    art = _segments()
    if s.empty:
        return pd.Series([], dtype=object, index=s.index)
    probs = _score(_feature_frame(s))
    feats = pd.DataFrame({"annual_cost_qar": s["annual_cost_qar"], "risk_prob": probs,
                          "age": s["age"], "care_gap_count": s["care_gap_count"],
                          "admissions_12mo": s["admissions_12mo"]})[art["features"]]
    labels = art["kmeans"].predict(art["scaler"].transform(feats))
    return pd.Series([art["segment_names"][int(l)] for l in labels], index=s.index)


def segment_summary(df: pd.DataFrame | None = None) -> dict:
    s = hie.summary() if df is None else df
    if s.empty:
        return {"segments": [], "scatter_sample": []}
    probs = _score(_feature_frame(s))
    s2 = s.assign(segment=segment_labels(s).values, risk_prob=probs)
    g = s2.groupby("segment").agg(
        patients=("patient_id", "count"), mean_cost=("annual_cost_qar", "mean"),
        total_cost=("annual_cost_qar", "sum"), mean_risk=("risk_prob", "mean"),
        mean_gaps=("care_gap_count", "mean"), mean_age=("age", "mean")).round(2)
    return {"segments": [{"segment": k, **{c: (v.item() if hasattr(v, "item") else v)
                                           for c, v in row.items()}}
                         for k, row in g.iterrows()],
            "scatter_sample": s2.sample(min(600, len(s2)), random_state=1)[
                ["risk_prob", "annual_cost_qar", "segment"]].round(4).to_dict("records")}


def visit_forecast() -> dict:
    return json.loads((MODELS / "visit_forecast.json").read_text())


# ─────────────────────────── population risk scenarios ───────────────────────────
# Each scenario names an eligible cohort and a hypothetical change to the model's INPUTS.
# The cohort is re-scored through the same deterioration-risk model and the shift in the
# predicted-risk distribution is reported. Nothing here estimates a treatment effect: the
# model is predictive, so a change in predicted risk is the model's response to different
# inputs, not an estimate of events prevented or money saved.

SCENARIOS = {
    "intensification_cohort_hba1c": {
        "label": "Intensification-review cohort: HbA1c one point lower",
        "cohort": "Type 2, HbA1c ≥ 8% with obesity, CKD or albuminuria, not on an SGLT2i / GLP-1 RA",
        "eligible": lambda s: (s["diabetes_type"] == "type2") & (s["on_sglt2_glp1"] == 0)
                              & (s["hba1c_latest"] >= 8)
                              & ((s["bmi"] >= 30) | (s["ckd"] == 1) | (s["albuminuria"] == 1)),
        "apply": lambda cf: cf.assign(hba1c_latest=cf["hba1c_latest"] - 1.0),
        "inputs_changed": "HbA1c: 1.0 point lower",
    },
    "hba1c_recall": {
        "label": "Overdue-HbA1c cohort: a test recorded 60 days ago",
        "cohort": "Patients whose last HbA1c is more than 183 days old",
        "eligible": lambda s: s["hba1c_days_since_test"].fillna(9999) > 183,
        "apply": lambda cf: cf.assign(hba1c_days_since_test=60),
        "inputs_changed": "Days since HbA1c test: 60",
    },
    "adherence_support": {
        "label": "Low-adherence cohort: PDC at 0.85",
        "cohort": "Patients with medication adherence (PDC) below 0.60",
        "eligible": lambda s: s["adherence_pdc"] < 0.6,
        "apply": lambda cf: cf.assign(adherence_pdc=0.85),
        "inputs_changed": "Adherence (PDC): 0.85",
    },
    "bp_control": {
        "label": "Uncontrolled-hypertension cohort: BP 14/7 mmHg lower",
        "cohort": "Diabetes with hypertension and BP ≥ 140/90",
        "eligible": lambda s: (s["htn"] == 1) & (s["bp_controlled"] == 0),
        "apply": lambda cf: cf.assign(sbp_latest=np.maximum(cf["sbp_latest"] - 14, 126),
                                      dbp_latest=np.maximum(cf["dbp_latest"] - 7, 76)),
        "inputs_changed": "Systolic BP: 14 mmHg lower (floor 126); diastolic BP: 7 mmHg lower (floor 76)",
    },
}


def _band_counts(bands: list[str]) -> dict:
    return {b: int(sum(1 for x in bands if x == b)) for b in BAND_ORDER}


def risk_scenario(scenario: str) -> dict:
    """Population predictive-risk scenario: re-score an eligible cohort with a hypothetical
    change to the model's inputs and report how the predicted-risk distribution shifts.
    Never converts the shift into events prevented, savings or a return."""
    spec = SCENARIOS.get(scenario)
    if not spec:
        return {"error": f"unknown scenario '{scenario}'", "available": list(SCENARIOS)}
    s = hie.summary()
    s = s[s["consent_status"] != "restricted"]
    cohort = s[spec["eligible"](s).fillna(False)]
    if cohort.empty:
        return {"scenario": scenario, "label": spec["label"], "eligible_patients": 0,
                "disclaimer": SCENARIO_DISCLAIMER}

    booster, features, _ = _risk()
    X0 = _feature_frame(cohort)
    X1 = _feature_frame(spec["apply"](cohort.copy()))
    p0, p1 = _score(X0), _score(X1)
    c0 = booster.predict(DMatrix(X0), pred_contribs=True)[:, :-1]     # last column is the bias
    c1 = booster.predict(DMatrix(X1), pred_contribs=True)[:, :-1]
    mean_delta = (c1 - c0).mean(axis=0)
    total = float(np.abs(mean_delta).sum()) or 1.0
    attribution = [{"feature": f, "label": FEATURE_LABELS.get(f, f),
                    "mean_delta_logodds": round(float(d), 4),
                    "share_of_change_pct": round(abs(float(d)) / total * 100, 1)}
                   for f, d in sorted(zip(features, mean_delta), key=lambda t: -abs(t[1]))
                   if abs(float(d)) >= 1e-4][:5]

    b0 = [_band(float(p)) for p in p0]
    b1 = [_band(float(p)) for p in p1]
    order = {b: i for i, b in enumerate(BAND_ORDER)}
    lower = sum(1 for a, b in zip(b0, b1) if order[b] < order[a])
    higher = sum(1 for a, b in zip(b0, b1) if order[b] > order[a])
    trans: dict = {}
    for a, b in zip(b0, b1):
        if a != b:
            trans[(a, b)] = trans.get((a, b), 0) + 1
    transitions = [{"from": a, "to": b, "patients": n}
                   for (a, b), n in sorted(trans.items(), key=lambda t: -t[1])]

    def dist(p, bands):
        return {"mean_predicted_risk": round(float(np.mean(p)), 4),
                "median_predicted_risk": round(float(np.median(p)), 4),
                "p90_predicted_risk": round(float(np.percentile(p, 90)), 4),
                "bands": _band_counts(bands)}

    return {
        "scenario": scenario, "label": spec["label"], "cohort": spec["cohort"],
        "inputs_changed": spec["inputs_changed"], "eligible_patients": int(len(cohort)),
        "baseline": dist(p0, b0), "hypothetical": dist(p1, b1),
        "band_movement": {"to_lower_band": int(lower), "unchanged": int(len(cohort) - lower - higher),
                          "to_higher_band": int(higher), "transitions": transitions},
        "feature_attribution": attribution,
        "disclaimer": SCENARIO_DISCLAIMER,
        "method": ("Every eligible patient is re-scored through the deployed deterioration-risk model with "
                   "the stated inputs changed; the shift is the model's response to different inputs, "
                   "attributed with SHAP-style pred_contribs. " + SCENARIO_DISCLAIMER),
    }
