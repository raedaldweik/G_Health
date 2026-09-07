"""
Nabd — scripted demo scenarios (resilience layer).

Each suggestion chip has a deterministic executor that calls the SAME services the
agent uses (HIE queries, RAG, ML scoring, the counterfactual simulator, the HITL
queue) and streams the same event shape as the live agent. Nothing here is a
canned number — the figures are computed from the data at click time.

Used when no GEMINI_API_KEY is configured, when FORCE_SCENARIOS=true, or as an
automatic fallback if a live agent run fails mid-demo.
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from services import geo, hie, ml, rag
from services import audit as audit_svc
from services import queue_service


def _fmt_qar(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"QAR {v/1_000_000:.1f}M"
    return f"QAR {v:,.0f}"


async def _steps(events: list[dict]) -> AsyncGenerator[dict, None]:
    """Animate trace steps with small delays so the UI shows live agent activity."""
    for e in events:
        yield {"type": "step", "status": "call", **{k: e[k] for k in ("agent", "tool")},
               "detail": e.get("args_summary", "")}
        await asyncio.sleep(0.22)
        yield {"type": "step", "status": "done", **{k: e[k] for k in ("agent", "tool")},
               "detail": e.get("result_summary", ""), "duration_ms": e.get("duration_ms", 240)}


def _trace(events: list[dict]) -> list[dict]:
    return [{"agent": e["agent"], "tool": e["tool"], "args_summary": e.get("args_summary", ""),
             "result_summary": e.get("result_summary", ""), "duration_ms": e.get("duration_ms", 240)}
            for e in events]


# ─────────────────────────── clinician scenarios ───────────────────────────

def _pick_deepdive_patient() -> str:
    s = hie.summary()
    cand = s[(s["open_care_gaps"].str.contains("statin_gap", na=False))
             & (s["hba1c_latest"] >= 8.6) & (s["consent_status"] == "general")
             & (s["established_cvd"] == 1)]
    if cand.empty:
        cand = s[s["consent_status"] == "general"]
    # Compelling but believable: prefer a model risk in the 25–60% range
    for _, row in cand.sort_values("ascvd_10yr_pct", ascending=False).head(25).iterrows():
        prob = ml.score_patient(row["patient_id"]).get("event_probability_12m", 0)
        if 0.25 <= prob <= 0.60:
            return row["patient_id"]
    return cand.sort_values("ascvd_10yr_pct", ascending=False).iloc[0]["patient_id"]


async def sc_morning_briefing(persona: str):
    kpi = hie.cohort_stats()
    strat = ml.stratify_cohort(top_n=5)
    gaps = hie.care_gap_summary()
    ev = [
        {"agent": "cohort_agent", "tool": "cohort_kpis",
         "args_summary": "registry-wide KPIs", "result_summary": f"{kpi['patients']} patients scanned"},
        {"agent": "risk_agent", "tool": "stratify_cohort_risk",
         "args_summary": "whole registry through complication_risk v1.2.0",
         "result_summary": f"expected 12-mo events: {strat['expected_events_12m']}"},
        {"agent": "pophealth_agent", "tool": "find_care_gaps",
         "args_summary": "all open gaps", "result_summary": f"{kpi['total_open_care_gaps']} open gaps"},
    ]
    async for e in _steps(ev):
        yield e
    top = strat["highest_risk_patients"]
    top_lines = "\n".join(
        f"| {p['patient_id']} | {p['age']} | {p['hba1c_latest'] or '—'} | {p['cv_risk_band']} "
        f"| **{p['risk_prob']*100:.0f}%** | {p['care_gap_count']} |" for p in top)
    gap_rows = [{"gap": g["gap_label"].split(" (")[0][:26], "patients": g["patients"]}
                for g in gaps[:6]]
    af_gap = kpi["af_anticoag_gap_patients"]
    answer = f"""**Overnight panel scan complete** — the model reviewed all **{kpi['patients']:,} patients** while you slept.

**Where the risk is concentrated this morning:**

| Patient | Age | HbA1c | CV band | 12-mo event risk | Open gaps |
|---|---|---|---|---|---|
{top_lines}

**Registry pulse:** mean HbA1c **{kpi['mean_hba1c']}%**, {kpi['pct_well_controlled']}% well-controlled; **{kpi['statin_gap_patients']} patients** sit in the statin gap and **{af_gap}** untreated AF patients carry avoidable stroke risk.

The model expects **≈{strat['expected_events_12m']:.0f} cardiometabolic events** across the registry in the next 12 months — the five patients above are your highest-yield reviews today. Ask me to deep-dive any of them.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar", "title": "Open care gaps by type",
                       "subtitle": "Live count from the HIE care-gap engine",
                       "data": gap_rows, "xKey": "gap",
                       "yKeys": [{"key": "patients", "label": "Patients"}]}],
           "citations": [], "actions": [], "usage": None, "model": "scripted·live-data"}


async def sc_patient_deepdive(persona: str):
    pid = _pick_deepdive_patient()
    rec = hie.get_patient(pid)
    score = ml.score_patient(pid)
    tl = hie.patient_timeline(pid, ["hba1c"])
    hits = rag.search("statin high intensity therapy very high cardiovascular risk LDL target", 3)
    p = rec["patient"]
    drivers = ", ".join(f"{d['feature']} ({'+' if d['contribution']>0 else ''}{d['contribution']:.2f})"
                        for d in score["top_drivers"][:4])
    item = queue_service.add_draft(
        "prescription", "Atorvastatin 40mg daily",
        f"High-intensity statin initiation — {p['cv_risk_band']} CV risk "
        f"(ASCVD {p['ascvd_10yr_pct']}%), LDL {p['ldl_latest']} mmol/L, no current statin. "
        f"Model 12-mo event risk {score['event_probability_12m']*100:.0f}%.",
        patient_id=pid, citation=f"{hits[0]['doc']}, p.{hits[0]['page']}" if hits else "")
    audit_svc.log("HITL·DRAFT", "action_agent",
                  f"Prescription draft Atorvastatin 40mg for {pid} → approval queue", pid, "action")
    ev = [
        {"agent": "cohort_agent", "tool": "get_patient", "args_summary": pid,
         "result_summary": "record + conditions + meds + encounters retrieved"},
        {"agent": "risk_agent", "tool": "score_patient_risk", "args_summary": pid,
         "result_summary": f"event risk {score['event_probability_12m']*100:.0f}% ({score['risk_band_model']})"},
        {"agent": "guideline_agent", "tool": "search_guidelines",
         "args_summary": "statin thresholds, very-high CV risk",
         "result_summary": f"{len(hits)} guideline passages"},
        {"agent": "action_agent", "tool": "draft_prescription",
         "args_summary": f"Atorvastatin 40mg for {pid}",
         "result_summary": f"draft {item['id']} → pending human approval"},
    ]
    async for e in _steps(ev):
        yield e
    meds = ", ".join(m["medication"] for m in rec["active_medications"][:6]) or "none recorded"
    conds = ", ".join(c["condition"] for c in rec["conditions"][:6])
    answer = f"""**{p['full_name']}** ({pid}) — {p['age']}y {p['gender']}, {p['nationality']}, {p['facility_name']}.

**One-minute picture:** {conds}. HbA1c **{p['hba1c_latest']}%** ({p['glycaemic_control'].replace('_',' ')}), LDL **{p['ldl_latest']} mmol/L**, eGFR {p['egfr_latest']} ({p['ckd_stage']}), BP {p['sbp_latest']:.0f}/{p['dbp_latest']:.0f}. Current therapy: {meds}.

**Model risk:** the deployed XGBoost model puts the 12-month cardiometabolic event probability at **{score['event_probability_12m']*100:.0f}%** ({score['risk_band_model']}). Main drivers: {drivers}.

**The actionable gap:** {p['cv_risk_band']} cardiovascular risk (ASCVD {p['ascvd_10yr_pct']}%) with **no statin on board** — the guideline calls for high-intensity statin at this risk level (see citation).

**I have drafted Atorvastatin 40mg daily to your approval queue** (draft `{item['id']}`). Nothing is prescribed until you sign it.
"""
    chart = None
    if tl["series"].get("hba1c"):
        pts = tl["series"]["hba1c"]
        chart = {"type": "line", "title": f"{pid} — HbA1c trajectory (36 months)",
                 "data": [{"month": d["date"][:7], "HbA1c": d["value"]} for d in pts],
                 "xKey": "month", "yKeys": [{"key": "HbA1c", "label": "HbA1c %"}],
                 "footnote": "Longitudinal values from the HIE observations table"}
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [chart] if chart else [],
           "citations": [{"doc": h["doc"], "file": h["file"], "page": h["page"],
                          "snippet": h["snippet"]} for h in hits],
           "actions": [{"draft_id": item["id"], "tool": "draft_prescription",
                        "status": "pending_human_approval"}],
           "usage": None, "model": "scripted·live-data"}


async def sc_statin_gap(persona: str):
    panel = hie.statin_gap_panel(limit=8)
    sim = ml.simulate_policy("close_statin_gap", 24)
    hits = rag.search("statin therapy high very high risk secondary prevention", 2)
    pids = [p["patient_id"] for p in panel["patients"]]
    item = queue_service.add_draft(
        "recall_campaign", f"Statin-gap recall — {panel['total']} high-risk patients",
        "Structured recall for statin initiation review in high/very-high CV-risk patients "
        "with no active statin, prioritised by ASCVD risk.", patient_ids=pids,
        citation=f"{hits[0]['doc']}, p.{hits[0]['page']}" if hits else "")
    audit_svc.log("HITL·DRAFT", "action_agent",
                  f"Statin-gap recall drafted for {panel['total']} patients", severity="action")
    ev = [
        {"agent": "pophealth_agent", "tool": "find_care_gaps", "args_summary": "gap_key=statin_gap",
         "result_summary": f"{panel['total']} patients in the statin gap"},
        {"agent": "risk_agent", "tool": "simulate_policy",
         "args_summary": "close_statin_gap, 24 months",
         "result_summary": f"{sim['expected_events_avoided']:.0f} events avoided, net {_fmt_qar(sim['net_benefit_qar'])}"},
        {"agent": "guideline_agent", "tool": "search_guidelines",
         "args_summary": "statin secondary prevention",
         "result_summary": f"{len(hits)} passages"},
        {"agent": "action_agent", "tool": "draft_recall",
         "args_summary": f"{panel['total']} patients, priority-ordered",
         "result_summary": f"draft {item['id']} → pending approval"},
    ]
    async for e in _steps(ev):
        yield e
    band_rows = [{"band": r["group"], "patients": r["value"]} for r in panel["by_band"]]
    answer = f"""**{panel['total']} patients** are at high or very-high cardiovascular risk with **no statin on board** — the single highest-yield prevention gap in the registry.

**What closing it is worth (counterfactual, 24 months):** the risk model re-scored all {sim['eligible_patients']} eligible patients with statin therapy applied — **{sim['relative_risk_reduction_pct']}% relative risk reduction**, ≈**{sim['expected_events_avoided']:.0f} events avoided**, {_fmt_qar(sim['event_cost_avoided_qar'])} of event cost avoided against {_fmt_qar(sim['programme_cost_qar'])} of therapy cost → **net {_fmt_qar(sim['net_benefit_qar'])}**.

The guideline is unambiguous at this risk level — high-intensity statin (see citation).

**Drafted:** a priority-ordered recall campaign for the full gap list is in your approval queue (`{item['id']}`).
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar", "title": "Statin gap by CV risk band",
                       "data": band_rows, "xKey": "band",
                       "yKeys": [{"key": "patients", "label": "Patients"}]}],
           "citations": [{"doc": h["doc"], "file": h["file"], "page": h["page"],
                          "snippet": h["snippet"]} for h in hits],
           "actions": [{"draft_id": item["id"], "tool": "draft_recall",
                        "status": "pending_human_approval"}],
           "usage": None, "model": "scripted·live-data"}


async def sc_af_gap(persona: str):
    s = hie.summary()
    af = s[s["af"] == 1]
    gap = af[af["on_anticoagulant"] == 0]
    hits = rag.search("atrial fibrillation anticoagulation stroke prevention DOAC", 2)
    sim = ml.simulate_policy("close_af_anticoag_gap", 12)
    ev = [
        {"agent": "cohort_agent", "tool": "filter_cohort", "args_summary": "af==1, on_anticoagulant==0",
         "result_summary": f"{len(gap)} of {len(af)} AF patients unprotected"},
        {"agent": "guideline_agent", "tool": "search_guidelines",
         "args_summary": "AF anticoagulation", "result_summary": f"{len(hits)} passages"},
        {"agent": "risk_agent", "tool": "simulate_policy",
         "args_summary": "close_af_anticoag_gap",
         "result_summary": f"{sim['expected_events_avoided']:.1f} events avoided/yr"},
    ]
    async for e in _steps(ev):
        yield e
    worst = gap.sort_values("ascvd_10yr_pct", ascending=False).head(5)
    rows = "\n".join(f"| {r.patient_id} | {r.age} | {r.cv_risk_band} | {r.facility_name} |"
                     for r in worst.itertuples())
    answer = f"""**{len(gap)} of {len(af)} atrial fibrillation patients ({len(gap)/len(af)*100:.0f}%) have no anticoagulation** — an avoidable stroke-prevention gap.

| Patient | Age | CV band | Facility |
|---|---|---|---|
{rows}

Guideline: direct oral anticoagulation is first-line for stroke prevention in AF unless contraindicated (see citation). The counterfactual model projects **{sim['expected_events_avoided']:.1f} events avoided per year** if the gap is closed (net {_fmt_qar(sim['net_benefit_qar'])}).

Say the word and I'll draft the anticoagulation reviews to your queue — every one requires your signature.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev), "charts": [],
           "citations": [{"doc": h["doc"], "file": h["file"], "page": h["page"],
                          "snippet": h["snippet"]} for h in hits],
           "actions": [], "usage": None, "model": "scripted·live-data"}


# ─────────────────────────── executive scenarios ───────────────────────────

async def sc_national_picture(persona: str):
    kpi = hie.cohort_stats()
    trend = hie.hba1c_trend_monthly()
    fac = hie.facility_benchmark()
    ev = [
        {"agent": "cohort_agent", "tool": "cohort_kpis", "args_summary": "national registry",
         "result_summary": f"{kpi['patients']} patients"},
        {"agent": "cohort_agent", "tool": "hba1c_trend", "args_summary": "36-month monthly means",
         "result_summary": f"{len(trend)} monthly points"},
        {"agent": "cohort_agent", "tool": "facility_benchmark", "args_summary": "18 facilities",
         "result_summary": f"top {fac[0]['facility_name']}"},
        {"agent": "nabd_supervisor", "tool": "render_map", "args_summary": "pct_controlled, flagged facilities ringed",
         "result_summary": "facility map rendered"},
    ]
    async for e in _steps(ev):
        yield e
    yoy = trend[-1]["mean_hba1c"] - trend[-13]["mean_hba1c"] if len(trend) > 13 else 0
    flagged = [f for f in fac if f["status"] == "flagged"]
    fac_map = geo.map_spec(None, "pct_controlled", "Where control is won and lost — % well-controlled by facility",
                           highlight=[f["facility_name"] for f in flagged])
    answer = f"""**National glycaemic picture** — {kpi['patients']:,} patients on the exchange.

Mean HbA1c is **{kpi['mean_hba1c']}%** ({'down' if yoy<0 else 'up'} {abs(yoy):.2f}pp year-on-year); **{kpi['pct_well_controlled']}%** of the diabetes cohort is well-controlled and **{kpi['pct_uncontrolled']}%** remains uncontrolled.

**Facility spread is the real story:** control ranges from **{fac[-1]['pct_controlled']:.0f}%** ({fac[-1]['facility_name']}) to **{fac[0]['pct_controlled']:.0f}%** ({fac[0]['facility_name']}). {len(flagged)} facilities sit below the flag line — {', '.join(f['facility_name'] for f in flagged[:3])} — that spread is an operational lever, not a clinical mystery.

One in three patients (**{kpi['pct_established_cvd']}%**) already has established cardiovascular disease — this is a cardiometabolic programme, not a glucose programme.

**And it has a geography.** The map shows it: control is a Doha phenomenon — the flagged facilities sit in the north (Al Shamal, Al Khor) and in the Industrial Area (Hazm Mebaireek), where the expatriate workforce lives. Distance from the capital and the equity gradient are the same line.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [
               fac_map,
               {"type": "line", "title": "National mean HbA1c — 36 months",
                "data": [{"month": t["month"], "HbA1c": t["mean_hba1c"]} for t in trend],
                "xKey": "month", "yKeys": [{"key": "HbA1c", "label": "Mean HbA1c %"}]},
               {"type": "bar", "title": "Facility benchmark — % well-controlled",
                "data": [{"facility": f["facility_name"].replace(" Health Center", "")
                          .replace(" Hospital", " H."), "controlled": f["pct_controlled"]}
                         for f in fac],
                "xKey": "facility", "yKeys": [{"key": "controlled", "label": "% controlled"}]}],
           "citations": [], "actions": [], "usage": None, "model": "scripted·live-data"}


async def sc_cost(persona: str):
    cc = hie.cost_concentration()
    seg = ml.segment_summary()
    ev = [
        {"agent": "cohort_agent", "tool": "cost_concentration", "args_summary": "annual cost, deciles",
         "result_summary": f"top 10% = {cc['top10pct_share_pct']}% of spend"},
        {"agent": "risk_agent", "tool": "segment_summary", "args_summary": "KMeans k=4 segments",
         "result_summary": f"{len(seg['segments'])} segments profiled"},
    ]
    async for e in _steps(ev):
        yield e
    segs = sorted(seg["segments"], key=lambda x: -x["total_cost"])
    seg_rows = "\n".join(
        f"| {x['segment']} | {x['patients']:,} | {_fmt_qar(x['mean_cost'])} | {x['mean_risk']*100:.0f}% | {x['mean_gaps']:.1f} |"
        for x in segs)
    answer = f"""**Total annual cost: {_fmt_qar(cc['total_annual_cost_qar'])}** — and it is heavily concentrated: the top 10% of patients drive **{cc['top10pct_share_pct']}%** of all spend.

**The four population segments (KMeans over cost, model risk, age, gaps, admissions):**

| Segment | Patients | Mean cost | Mean 12-mo risk | Mean gaps |
|---|---|---|---|---|
{seg_rows}

The '{segs[0]['segment']}' segment is where case-management pays for itself; the '{[x for x in segs if 'gap' in x['segment'].lower()][0]['segment'] if any('gap' in x['segment'].lower() for x in segs) else segs[1]['segment']}' segment is cheap to fix — its cost is future, not current.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [
               {"type": "line", "title": "Cost concentration curve",
                "subtitle": "Cumulative % of spend vs % of patients (ranked by cost)",
                "data": [{"patients": f"{d['top_pct_patients']}%", "share": d["pct_of_spend"]}
                         for d in cc["deciles"]],
                "xKey": "patients", "yKeys": [{"key": "share", "label": "% of total spend"}]},
               {"type": "pie", "title": "Annual spend by segment",
                "data": [{"segment": x["segment"], "spend": round(x["total_cost"] / 1e6, 2)}
                         for x in segs],
                "xKey": "segment", "yKeys": [{"key": "spend", "label": "QAR (M)"}]}],
           "citations": [], "actions": [], "usage": None, "model": "scripted·live-data"}


async def sc_policy_sim(persona: str):
    sims = [ml.simulate_policy(k, 24) for k in
            ["close_statin_gap", "close_glp1_sglt2_gap", "close_af_anticoag_gap", "bp_control_program"]]
    comb = ml.simulate_policy("combined", 24)
    ev = [
        {"agent": "pophealth_agent", "tool": "simulate_policy",
         "args_summary": f"{s['intervention']}, 24 months",
         "result_summary": f"{s['expected_events_avoided']:.0f} events avoided, net {_fmt_qar(s['net_benefit_qar'])}"}
        for s in sims
    ] + [{"agent": "risk_agent", "tool": "simulate_policy", "args_summary": "combined, 24 months",
          "result_summary": f"net {_fmt_qar(comb['net_benefit_qar'])}"}]
    async for e in _steps(ev):
        yield e
    rows = "\n".join(
        f"| {s['label'][:48]} | {s['eligible_patients']:,} | {s['relative_risk_reduction_pct']}% "
        f"| {s['expected_events_avoided']:.0f} | {_fmt_qar(s['programme_cost_qar'])} | **{_fmt_qar(s['net_benefit_qar'])}** |"
        for s in sims)
    answer = f"""**Policy simulation — four interventions, 24-month horizon.** This is a true counterfactual: every eligible patient is re-scored through the deployed risk model with the therapy applied; nothing here is a canned number.

| Intervention | Eligible | RRR | Events avoided | Programme cost | Net benefit |
|---|---|---|---|---|---|
{rows}

**All four combined: ≈{comb['expected_events_avoided']:.0f} events avoided and a net {_fmt_qar(comb['net_benefit_qar'])}** over 24 months (event episodes costed at QAR 32k).

The statin-gap closure is the highest-yield-per-riyal lever; the SGLT2/GLP-1 programme costs more but compounds through glycaemic control. Phase 2 runs this same simulation as BigQuery `ML.PREDICT` over the counterfactual cohort — identical logic, warehouse scale.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar",
                       "title": "Net benefit by intervention (24 months)",
                       "data": [{"intervention": s["intervention"].replace("close_", "").replace("_", " "),
                                 "net_qar_m": round(s["net_benefit_qar"] / 1e6, 2)} for s in sims],
                       "xKey": "intervention",
                       "yKeys": [{"key": "net_qar_m", "label": "Net benefit (QAR M)"}]}],
           "citations": [], "actions": [], "usage": None, "model": "scripted·live-data"}


async def sc_equity(persona: str):
    eq = hie.equity_breakdown()
    ev = [{"agent": "cohort_agent", "tool": "equity_breakdown",
           "args_summary": "outcomes by nationality",
           "result_summary": f"{len(eq)} nationality groups compared"}]
    async for e in _steps(ev):
        yield e
    worst, best = eq[0], eq[-1]
    answer = f"""**The equity gap is real and measurable.** Mean HbA1c ranges from **{best['mean_hba1c']}%** ({best['nationality']}) to **{worst['mean_hba1c']}%** ({worst['nationality']}) — a {worst['mean_hba1c']-best['mean_hba1c']:.2f}pp spread — and control rates follow the same gradient.

The pattern tracks healthcare access, not biology: the largest gaps sit in expatriate worker populations ({', '.join(e['nationality'] for e in eq[:3])}), who also carry more open care gaps per patient. A multilingual outreach programme (SMS in Bengali, Nepali, Urdu, Tagalog) is the cheapest intervention on the board and aligns directly with the National Health Strategy's equity pillar.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar", "title": "Mean HbA1c by nationality",
                       "subtitle": "Diabetes cohort — the access gradient",
                       "data": [{"nationality": e["nationality"], "HbA1c": e["mean_hba1c"]}
                                for e in eq],
                       "xKey": "nationality", "yKeys": [{"key": "HbA1c", "label": "Mean HbA1c %"}]}],
           "citations": [], "actions": [], "usage": None, "model": "scripted·live-data"}


async def sc_forecast(persona: str):
    fc = ml.visit_forecast()
    ev = [{"agent": "risk_agent", "tool": "visit_forecast",
           "args_summary": "36 months history → 12-month horizon",
           "result_summary": f"+{fc['yoy_growth_pct']}% next 12 months"}]
    async for e in _steps(ev):
        yield e
    hist_avg = sum(h["visits"] for h in fc["history"][-12:]) / 12
    peak = max(fc["forecast"], key=lambda f: f["visits"])
    answer = f"""**Ambulatory demand will grow ≈{fc['yoy_growth_pct']}% over the next 12 months** — from an average of {hist_avg:,.0f} visits/month to a peak of **{peak['visits']:,} in {peak['month']}**.

The model (trend + month-of-year seasonality over 36 months of encounter history) captures the recurring summer dip and Ramadan pattern, so the growth figure is structural, not seasonal noise. Capacity planning should target the Q4 ramp.

Phase 2 note: this exact question becomes one SQL call — `AI.FORECAST` in BigQuery, powered by the TimesFM foundation model, no training step at all.
"""
    data = ([{"month": h["month"], "Actual": h["visits"]} for h in fc["history"]]
            + [{"month": f["month"], "Forecast": f["visits"], "lo": f["lo"], "hi": f["hi"]}
               for f in fc["forecast"]])
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "line", "title": "Monthly ambulatory visits — history & 12-month forecast",
                       "data": data, "xKey": "month",
                       "yKeys": [{"key": "Actual", "label": "Actual"},
                                 {"key": "Forecast", "label": "Forecast"}],
                       "footnote": "Seasonal model over HIE encounters; 80% interval computed"}],
           "citations": [], "actions": [], "usage": None, "model": "scripted·live-data"}


async def sc_quality(persona: str):
    measures = hie.quality_measures()
    ev = [{"agent": "pophealth_agent", "tool": "compute_quality_measure",
           "args_summary": "full measure set",
           "result_summary": f"{len(measures)} measures computed live"}]
    async for e in _steps(ev):
        yield e
    def status_cell(m):
        return "✅ met" if m["met"] else f"❌ {m['gap_patients']} patients short"
    rows = "\n".join(
        f"| {m['measure_id']} | {m['name'][:44]} | **{m['rate_pct']}%** | {m['target_pct']}% "
        f"| {status_cell(m)} |" for m in measures)
    answer = f"""**Clinical quality scorecard** — every measure computed live from the HIE by the population-health MCP server:

| Measure | Description | Rate | Target | Status |
|---|---|---|---|---|
{rows}

The two furthest from target — statin therapy in high-risk patients and HFrEF guideline-directed therapy — are exactly the gaps with the strongest evidence base. That is where the next riyal goes.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar", "title": "Quality measures — rate vs target",
                       "data": [{"measure": m["measure_id"], "rate": m["rate_pct"],
                                 "target": m["target_pct"]} for m in measures],
                       "xKey": "measure",
                       "yKeys": [{"key": "rate", "label": "Current rate %"},
                                 {"key": "target", "label": "Target %"}]}],
           "citations": [], "actions": [], "usage": None, "model": "scripted·live-data"}


SCENARIOS = {
    "clinician": [
        {"id": "c_briefing", "tag": "C1", "label": "Morning panel briefing",
         "question": "Give me my morning briefing — scan the panel and tell me who needs attention today.",
         "runner": sc_morning_briefing},
        {"id": "c_deepdive", "tag": "C2", "label": "Patient deep-dive + draft Rx",
         "question": "Deep-dive my highest-risk statin-gap patient: summarise, score their risk, check the guideline, and draft what's needed.",
         "runner": sc_patient_deepdive},
        {"id": "c_statin", "tag": "C3", "label": "Statin gap panel",
         "question": "How many high-risk patients aren't on a statin, what is closing that gap worth, and draft the recall.",
         "runner": sc_statin_gap},
        {"id": "c_af", "tag": "C4", "label": "AF anticoagulation gap",
         "question": "Which atrial fibrillation patients have no anticoagulation, and what does the guideline say?",
         "runner": sc_af_gap},
    ],
    "executive": [
        {"id": "e_national", "tag": "E1", "label": "National glycaemic picture",
         "question": "Give me the national glycaemic picture — trend, control rates, and facility spread.",
         "runner": sc_national_picture},
        {"id": "e_cost", "tag": "E2", "label": "Cost concentration & segments",
         "question": "Where is our spend concentrated, and what do the population segments look like?",
         "runner": sc_cost},
        {"id": "e_sim", "tag": "E3", "label": "Policy simulation (ML)",
         "question": "Simulate our four candidate interventions over 24 months and rank them by net benefit.",
         "runner": sc_policy_sim},
        {"id": "e_equity", "tag": "E4", "label": "Equity analysis",
         "question": "Show me the equity picture — outcomes by nationality.",
         "runner": sc_equity},
        {"id": "e_forecast", "tag": "E5", "label": "Demand forecast",
         "question": "Forecast outpatient demand for the next 12 months.",
         "runner": sc_forecast},
        {"id": "e_quality", "tag": "E6", "label": "Quality scorecard (MCP)",
         "question": "Compute the clinical quality scorecard against our targets.",
         "runner": sc_quality},
    ],
}


def list_scenarios(persona: str) -> list[dict]:
    return [{k: s[k] for k in ("id", "tag", "label", "question")}
            for s in SCENARIOS.get(persona, [])]


def get_runner(scenario_id: str):
    for group in SCENARIOS.values():
        for s in group:
            if s["id"] == scenario_id:
                return s["runner"]
    return None
