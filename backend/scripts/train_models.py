"""
Nabd — model training pipeline.

Trains the real ML models that power the platform (no mocked numbers anywhere):

  1. complication_risk   XGBoost classifier — P(cardiometabolic event, next 12 months).
                         Explainable per-patient via XGBoost pred_contribs (SHAP values).
                         Also drives the counterfactual policy simulator (flip treatment
                         flags → re-score the cohort → aggregate predicted event change).
  2. cohort_segments     KMeans (k=4) over cost/risk/utilisation → named population segments.
  3. patient_similarity  NearestNeighbors over standardised clinical features.
  4. visit_forecast      Seasonal linear model over 36 monthly visit counts → 12-month
                         forecast with intervals. (Phase 2 swaps this for BigQuery
                         AI.FORECAST / TimesFM.)

Artifacts land in backend/models/ together with model_cards.json (version, data,
features, metrics, intended use, limitations) — surfaced in the UI for governance.

Run from backend/:  python -m scripts.train_models
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data" / "hie"
OUT = HERE / "models"

RISK_FEATURES = [
    "age", "is_male", "bmi", "bmi_change_12m", "years_since_diagnosis", "smoker",
    "hba1c_latest", "hba1c_12m_ago", "hba1c_days_since_test", "sbp_latest", "dbp_latest",
    "egfr_latest", "acr_latest", "albuminuria", "retinopathy", "neuropathy", "foot_ulcer_history", "htn",
    "on_metformin", "on_sglt2_glp1", "on_insulin", "on_raas_inhibitor", "adherence_pdc",
    "admissions_12mo", "ed_visits_12mo", "diabetes_medication_count", "care_gap_count",
]
# Treatment / programme levers the counterfactual simulator may change
INTERVENABLE = ["on_sglt2_glp1", "on_raas_inhibitor", "adherence_pdc", "hba1c_days_since_test", "sbp_latest"]

SIM_FEATURES = ["age", "bmi", "hba1c_latest", "years_since_diagnosis", "sbp_latest", "egfr_latest",
                "acr_latest", "retinopathy", "neuropathy", "adherence_pdc", "admissions_12mo", "annual_cost_qar"]


def load_features() -> pd.DataFrame:
    s = pd.read_csv(DATA / "patient_summary.csv.gz")
    s["is_male"] = (s["gender"] == "male").astype(int)
    return s


def train_risk_model(s: pd.DataFrame) -> dict:
    X = s[RISK_FEATURES].copy()
    y = s["deterioration_next_12m"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=7, stratify=y)

    model = XGBClassifier(
        n_estimators=600, max_depth=3, learning_rate=0.035,
        subsample=0.85, colsample_bytree=0.8, min_child_weight=6,
        eval_metric="auc", random_state=7, n_jobs=2,
    )
    model.fit(X_tr, y_tr)

    p_te = model.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, p_te)
    ap = average_precision_score(y_te, p_te)

    # Decile calibration on the held-out set (risk vs observed event rate)
    dec = pd.DataFrame({"p": p_te, "y": y_te.values})
    dec["decile"] = pd.qcut(dec["p"], 10, labels=False, duplicates="drop") + 1
    calib = (dec.groupby("decile")
             .agg(mean_predicted=("p", "mean"), observed_rate=("y", "mean"), n=("y", "size"))
             .reset_index().round(4).to_dict(orient="records"))

    # Global importance (gain)
    booster = model.get_booster()
    gain = booster.get_score(importance_type="gain")
    fmap = {f"f{i}": name for i, name in enumerate(RISK_FEATURES)}
    importance = sorted(
        [{"feature": fmap.get(k, k), "gain": round(v, 2)} for k, v in gain.items()],
        key=lambda r: -r["gain"])

    # Compare against the legacy rules-based registry score
    legacy_auc = roc_auc_score(y_te, s.loc[X_te.index, "legacy_risk_score"])

    # Persist held-out predictions so the AI Evaluation tab computes ROC, calibration,
    # threshold sweeps and subgroup fairness from real test data (never training data).
    ev = s.loc[X_te.index, ["patient_id", "nationality", "gender", "age", "primary_facility_id",
                            "registry_risk_tier", "legacy_risk_score"]].copy()
    ev["y_true"] = y_te.values
    ev["p"] = p_te
    ev.to_csv(OUT / "eval_predictions.csv.gz", index=False, compression="gzip")

    booster.save_model(OUT / "complication_risk.xgb.json")
    (OUT / "complication_risk.features.json").write_text(json.dumps({
        "features": RISK_FEATURES, "intervenable": INTERVENABLE}))
    print(f"  complication_risk: AUC {auc:.3f} (legacy registry score {legacy_auc:.3f}), AP {ap:.3f}")
    return {"auc": round(auc, 3), "average_precision": round(ap, 3),
            "legacy_score_auc": round(legacy_auc, 3),
            "train_rows": len(X_tr), "test_rows": len(X_te),
            "event_rate": round(float(y.mean()), 3),
            "top_drivers": importance[:10], "calibration_deciles": calib}


def train_segments(s: pd.DataFrame, risk_prob: np.ndarray) -> dict:
    feats = pd.DataFrame({
        "annual_cost_qar": s["annual_cost_qar"],
        "risk_prob": risk_prob,
        "age": s["age"],
        "care_gap_count": s["care_gap_count"],
        "admissions_12mo": s["admissions_12mo"],
    })
    scaler = StandardScaler().fit(feats)
    km = KMeans(n_clusters=4, n_init=10, random_state=7).fit(scaler.transform(feats))
    s2 = feats.copy()
    s2["segment"] = km.labels_

    prof = s2.groupby("segment").mean().round(2)
    # Name segments by their profile, ordered by cost
    order = prof["annual_cost_qar"].sort_values(ascending=False).index.tolist()
    names = ["Complex high-cost", "Rising-risk", "Care-gap heavy", "Stable low-touch"]
    # Heuristic naming: highest cost → complex; highest risk of the rest → rising-risk;
    # highest gap count of the rest → care-gap heavy; remainder → stable.
    remaining = list(prof.index)
    mapping = {}
    c = prof["annual_cost_qar"].idxmax(); mapping[c] = "Complex high-cost"; remaining.remove(c)
    r = prof.loc[remaining, "risk_prob"].idxmax(); mapping[r] = "Rising-risk"; remaining.remove(r)
    g = prof.loc[remaining, "care_gap_count"].idxmax(); mapping[g] = "Care-gap heavy"; remaining.remove(g)
    mapping[remaining[0]] = "Stable low-touch"

    joblib.dump({"scaler": scaler, "kmeans": km, "features": list(feats.columns),
                 "segment_names": {int(k): v for k, v in mapping.items()}},
                OUT / "cohort_segments.joblib")
    sizes = {mapping[int(k)]: int(v) for k, v in s2["segment"].value_counts().items()}
    profile = {mapping[int(idx)]: row.to_dict() for idx, row in prof.iterrows()}
    print(f"  cohort_segments: {sizes}")
    return {"k": 4, "segment_sizes": sizes, "segment_profiles": profile,
            "inertia": round(float(km.inertia_), 1)}


def train_similarity(s: pd.DataFrame) -> dict:
    feats = s[SIM_FEATURES].fillna(s[SIM_FEATURES].median())
    scaler = StandardScaler().fit(feats)
    nn = NearestNeighbors(n_neighbors=12, metric="euclidean").fit(scaler.transform(feats))
    joblib.dump({"scaler": scaler, "nn": nn, "features": SIM_FEATURES,
                 "patient_ids": s["patient_id"].tolist()},
                OUT / "patient_similarity.joblib")
    print(f"  patient_similarity: {len(s)} patients indexed over {len(SIM_FEATURES)} features")
    return {"indexed_patients": len(s), "features": SIM_FEATURES, "metric": "euclidean (standardised)"}


def train_forecast() -> dict:
    enc = pd.read_csv(DATA / "encounters.csv.gz", parse_dates=["start_date"])
    amb = enc[enc["encounter_type"].isin(["outpatient", "telehealth"])]
    monthly = (amb.set_index("start_date").resample("MS").size().rename("visits").reset_index())
    monthly = monthly.iloc[:-1] if len(monthly) > 36 else monthly   # drop partial current month
    monthly["t"] = np.arange(len(monthly))
    monthly["month"] = monthly["start_date"].dt.month

    Xm = pd.get_dummies(monthly["month"], prefix="m").astype(float)
    X = pd.concat([monthly[["t"]], Xm], axis=1)
    model = Ridge(alpha=1.0).fit(X, monthly["visits"])
    resid_std = float(np.std(monthly["visits"] - model.predict(X)))

    # 12-month forecast
    future = []
    last_t = int(monthly["t"].iloc[-1])
    last_date = monthly["start_date"].iloc[-1]
    for k in range(1, 13):
        d = (last_date + pd.DateOffset(months=k))
        future.append({"t": last_t + k, "month": d.month, "start_date": d})
    fdf = pd.DataFrame(future)
    Xf = pd.concat([fdf[["t"]], pd.get_dummies(fdf["month"], prefix="m").astype(float)], axis=1)
    Xf = Xf.reindex(columns=X.columns, fill_value=0.0)
    fdf["forecast"] = model.predict(Xf).round(0)

    history = [{"month": d.strftime("%Y-%m"), "visits": int(v)}
               for d, v in zip(monthly["start_date"], monthly["visits"])]
    forecast = [{"month": r["start_date"].strftime("%Y-%m"), "visits": int(r["forecast"]),
                 "lo": int(r["forecast"] - 1.28 * resid_std), "hi": int(r["forecast"] + 1.28 * resid_std)}
                for _, r in fdf.iterrows()]
    growth = round((sum(f["visits"] for f in forecast) /
                    sum(h["visits"] for h in history[-12:]) - 1) * 100, 1)
    payload = {"history": history, "forecast": forecast, "residual_std": round(resid_std, 1),
               "yoy_growth_pct": growth}
    (OUT / "visit_forecast.json").write_text(json.dumps(payload))
    print(f"  visit_forecast: 36 months history → 12 months ahead (+{growth}% YoY)")
    return {"history_months": len(history), "horizon_months": 12,
            "yoy_growth_pct": growth, "method": "linear trend + month-of-year seasonality (Ridge)"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = load_features()
    print("Training models…")
    risk_metrics = train_risk_model(s)

    # Score the full cohort once for the segmentation features
    from xgboost import Booster, DMatrix
    booster = Booster(); booster.load_model(str(OUT / "complication_risk.xgb.json"))
    risk_prob = booster.predict(DMatrix(s[RISK_FEATURES]))

    seg_metrics = train_segments(s, risk_prob)
    sim_metrics = train_similarity(s)
    fc_metrics = train_forecast()

    today = date.today().isoformat()
    cards = [
        {"model_id": "complication_risk", "name": "Diabetes Deterioration Risk",
         "version": "2.0.0", "trained": today, "framework": "XGBoost (gradient-boosted trees)",
         "task": "Binary classification — P(diabetes deterioration event within 12 months: admission for hypo/hyperglycaemia, DKA/HHS, foot infection or AKI, or progression to HbA1c ≥ 10%)",
         "training_data": f"{risk_metrics['train_rows']} patients (held-out test: {risk_metrics['test_rows']}), synthetic QHIE cohort",
         "features": RISK_FEATURES, "metrics": risk_metrics,
         "intended_use": "Panel prioritisation for the diabetes programme, care-gap targeting, counterfactual programme simulation. Decision support only — never autonomous treatment decisions.",
         "limitations": "Trained on synthetic data; requires clinical validation and bias audit before any production use. Programme counterfactuals assume guideline-average effect sizes.",
         "phase2": "Retrain as BigQuery ML BOOSTED_TREE_CLASSIFIER, register to Vertex AI Model Registry, serve on an online endpoint, score via the official Agent Platform /mcp/predict toolset."},
        {"model_id": "cohort_segments", "name": "Population Segmentation",
         "version": "1.0.1", "trained": today, "framework": "scikit-learn KMeans (k=4)",
         "task": "Unsupervised segmentation over cost, model risk, age, care gaps, admissions",
         "training_data": "4,000 patients", "features": ["annual_cost_qar", "risk_prob", "age", "care_gap_count", "admissions_12mo"],
         "metrics": seg_metrics,
         "intended_use": "Executive cost-of-care narratives and programme design.",
         "limitations": "Segments are descriptive, not causal.",
         "phase2": "BigQuery ML KMEANS in SQL over the streamed FHIR export."},
        {"model_id": "patient_similarity", "name": "Patient Similarity Index",
         "version": "1.0.0", "trained": today, "framework": "scikit-learn NearestNeighbors",
         "task": "Find clinically similar diabetes patients (standardised feature space)",
         "training_data": "4,000 patients", "features": SIM_FEATURES, "metrics": sim_metrics,
         "intended_use": "'Patients like this one' clinical context and cohort matching.",
         "limitations": "Feature-space similarity, not outcome-matched controls.",
         "phase2": "gemini-embedding-001 patient embeddings + BigQuery VECTOR_SEARCH."},
        {"model_id": "visit_forecast", "name": "Ambulatory Demand Forecast",
         "version": "1.1.0", "trained": today, "framework": "Ridge regression (trend + seasonality)",
         "task": "12-month monthly outpatient/telehealth visit forecast with 80% interval",
         "training_data": "36 months of encounter volumes", "features": ["month trend", "month-of-year"],
         "metrics": fc_metrics,
         "intended_use": "Capacity planning and the executive demand narrative.",
         "limitations": "Univariate; no exogenous drivers (campaigns, epidemics).",
         "phase2": "BigQuery AI.FORECAST (TimesFM foundation model) — zero-training forecasting in one SQL call."},
    ]
    (OUT / "model_cards.json").write_text(json.dumps(cards, indent=2))
    print(f"\n✓ artifacts + model_cards.json written to {OUT}")


if __name__ == "__main__":
    main()
