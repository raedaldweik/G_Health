"""
Nabd, scripted demo scenarios (resilience layer).

Each suggestion chip has a deterministic executor that calls the SAME services the
agent uses (HIE queries, RAG, ML scoring, the counterfactual simulator, the HITL
queue) and streams the same event shape as the live agent. Nothing here is a
canned number, the figures are computed from the data at click time.

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
    """A type 2 patient in the intensification gap whose HbA1c is rising, the case the
    registry tier does not flag but the model does."""
    s = hie.summary()
    cand = s[(s["open_care_gaps"].str.contains("glp1_sglt2_gap", na=False))
             & (s["hba1c_latest"] >= 8.6) & (s["consent_status"] == "general")
             & (s["diabetes_type"] == "type2") & (s["on_metformin"] == 1)
             & (s["hba1c_12m_ago"].notna()) & (s["hba1c_latest"] > s["hba1c_12m_ago"] + 0.4)
             & (s["registry_risk_tier"].isin(["Low", "Moderate"]))]
    if cand.empty:
        cand = s[(s["open_care_gaps"].str.contains("glp1_sglt2_gap", na=False)) & (s["consent_status"] == "general")]
    if cand.empty:
        cand = s[s["consent_status"] == "general"]
    # Compelling but believable: prefer a model risk in the 25–60% range
    for _, row in cand.sort_values("hba1c_latest", ascending=False).head(40).iterrows():
        prob = ml.score_patient(row["patient_id"]).get("event_probability_12m", 0)
        if 0.25 <= prob <= 0.60:
            return row["patient_id"]
    return cand.sort_values("hba1c_latest", ascending=False).iloc[0]["patient_id"]


async def sc_morning_briefing(persona: str):
    kpi = hie.cohort_stats()
    strat = ml.stratify_cohort(top_n=5)
    gaps = hie.care_gap_summary()
    ev = [
        {"agent": "cohort_agent", "tool": "cohort_kpis",
         "args_summary": "registry-wide KPIs", "result_summary": f"{kpi['patients']} patients scanned"},
        {"agent": "risk_agent", "tool": "stratify_cohort_risk",
         "args_summary": "whole registry through deterioration_risk v2.1.0",
         "result_summary": f"expected 12-mo events: {strat['expected_events_12m']}"},
        {"agent": "pophealth_agent", "tool": "find_care_gaps",
         "args_summary": "all open gaps", "result_summary": f"{kpi['total_open_care_gaps']} open gaps"},
    ]
    async for e in _steps(ev):
        yield e
    top = strat["highest_risk_patients"]
    top_lines = "\n".join(
        f"| {p['patient_id']} | {p['age']} | {p['hba1c_latest'] or 'n/a'} | {p['registry_risk_tier']} "
        f"| **{p['risk_prob']*100:.0f}%** | {p['care_gap_count']} |" for p in top)
    gap_rows = [{"gap": g["gap_label"].split(" (")[0][:26], "patients": g["patients"]}
                for g in gaps[:6]]
    answer = f"""**Panel review complete.** The deterioration model scored all **{kpi['patients']:,} patients** in the registry overnight.

**Patients with the highest 12-month deterioration risk:**

| Patient | Age | HbA1c | Registry tier | 12-mo deterioration risk | Open gaps |
|---|---|---|---|---|---|
{top_lines}

**Registry summary:** mean HbA1c **{kpi['mean_hba1c']}%**; **{kpi['pct_well_controlled']}%** well-controlled (<7%) and **{kpi['pct_poorly_controlled']}%** poorly controlled (≥9%). **{kpi['hba1c_overdue_patients']} patients** are overdue for an HbA1c test, **{kpi['intensification_gap_patients']}** meet the criteria for treatment intensification, and **{kpi['low_adherence_patients']}** have adherence below 60%.

The model expects **≈{strat['expected_events_12m']:.0f} deterioration events** across the registry in the next 12 months. The five patients above are the highest-yield reviews today; ask for a deep-dive on any of them.
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
    hits = rag.search("type 2 diabetes HbA1c above target add SGLT2 inhibitor GLP-1 receptor agonist obesity chronic kidney disease", 3)
    p = rec["patient"]
    drivers = ", ".join(f"{d['feature']} ({'+' if d['contribution']>0 else ''}{d['contribution']:.2f})"
                        for d in score["top_drivers"][:4])
    renal = (p.get("ckd") == 1) or (p.get("albuminuria") == 1)
    drug = "Empagliflozin 10mg daily" if (renal or (p.get("egfr_latest") or 100) >= 30) else "Semaglutide 0.25mg weekly"
    why = ("CKD/albuminuria, renal and glycaemic benefit" if renal else "obesity with HbA1c above target")
    item = queue_service.add_draft(
        "prescription", drug,
        f"Treatment intensification, type 2 diabetes, HbA1c {p['hba1c_latest']}% "
        f"(from {p.get('hba1c_12m_ago') or 'n/a'}% a year ago) on metformin without an SGLT2i/GLP-1 RA; {why}. "
        f"BMI {p['bmi']}, eGFR {p['egfr_latest']}. Model 12-month deterioration risk {score['event_probability_12m']*100:.0f}%.",
        patient_id=pid, citation=f"{hits[0]['doc']}, p.{hits[0]['page']}" if hits else "")
    audit_svc.log("HITL·DRAFT", "action_agent",
                  f"Prescription draft {drug} for {pid} → approval queue", pid, "action")
    ev = [
        {"agent": "cohort_agent", "tool": "get_patient", "args_summary": pid,
         "result_summary": "record + conditions + meds + encounters retrieved"},
        {"agent": "risk_agent", "tool": "score_patient_risk", "args_summary": pid,
         "result_summary": f"deterioration risk {score['event_probability_12m']*100:.0f}% ({score['risk_band_model']})"},
        {"agent": "guideline_agent", "tool": "search_guidelines",
         "args_summary": "intensification: SGLT2i / GLP-1 RA when HbA1c above target",
         "result_summary": f"{len(hits)} guideline passages"},
        {"agent": "action_agent", "tool": "draft_prescription",
         "args_summary": f"{drug} for {pid}",
         "result_summary": f"draft {item['id']} → pending human approval"},
    ]
    async for e in _steps(ev):
        yield e
    meds = ", ".join(m["medication"] for m in rec["active_medications"][:6]) or "none recorded"
    conds = ", ".join(c["condition"] for c in rec["conditions"][:6])
    traj = (f"HbA1c **{p['hba1c_latest']}%**, up from {p['hba1c_12m_ago']}% twelve months ago"
            if p.get("hba1c_12m_ago") else f"HbA1c **{p['hba1c_latest']}%**")
    answer = f"""**{p['full_name']}** ({pid}), {p['age']}y {p['gender']}, {p['nationality']}, {p['facility_name']}. Type 2 diabetes for {p['years_since_diagnosis']} years.

**Clinical picture:** {conds}. {traj} ({p['glycaemic_control'].replace('_',' ')}); BMI **{p['bmi']}**; eGFR {p['egfr_latest']} ({p['ckd_stage']}); BP {p['sbp_latest']:.0f}/{p['dbp_latest']:.0f}; medication adherence {p['adherence_pdc']*100:.0f}% of days covered. Current therapy: {meds}.

**Model assessment:** the deterioration model puts the 12-month probability of a deterioration event at **{score['event_probability_12m']*100:.0f}%** ({score['risk_band_model']}); the registry's rule-based tier is **{p['registry_risk_tier']}**. Main drivers: {drivers}.

**The actionable gap:** HbA1c above target on metformin without an SGLT2 inhibitor or GLP-1 receptor agonist, with {why}. The national guideline recommends adding one of these agents at this point (see citation).

**Drafted for your approval:** {drug} (draft `{item['id']}`). Nothing is prescribed until you approve it.
"""
    chart = None
    if tl["series"].get("hba1c"):
        pts = tl["series"]["hba1c"]
        chart = {"type": "line", "title": f"{pid}: HbA1c trajectory (36 months)",
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


async def sc_intensification_gap(persona: str):
    panel = hie.gap_panel("glp1_sglt2_gap", limit=8)
    sim = ml.simulate_policy("sglt2_glp1_intensification", 24)
    hits = rag.search("SGLT2 inhibitor GLP-1 receptor agonist type 2 diabetes HbA1c above target obesity kidney", 2)
    pids = [p["patient_id"] for p in panel["patients"]]
    item = queue_service.add_draft(
        "recall_campaign", f"Treatment-intensification review, {panel['total']} patients",
        "Structured review for SGLT2i / GLP-1 RA initiation in type 2 patients with HbA1c ≥8% and "
        "obesity or kidney disease who are not yet on either agent, prioritised by HbA1c.", patient_ids=pids,
        citation=f"{hits[0]['doc']}, p.{hits[0]['page']}" if hits else "")
    audit_svc.log("HITL·DRAFT", "action_agent",
                  f"Intensification review drafted for {panel['total']} patients", severity="action")
    ev = [
        {"agent": "pophealth_agent", "tool": "find_care_gaps", "args_summary": "gap_key=glp1_sglt2_gap",
         "result_summary": f"{panel['total']} patients meet intensification criteria"},
        {"agent": "risk_agent", "tool": "simulate_policy",
         "args_summary": "sglt2_glp1_intensification, 24 months",
         "result_summary": f"{sim['expected_events_avoided']:.0f} events avoided, net {_fmt_qar(sim['net_benefit_qar'])}"},
        {"agent": "guideline_agent", "tool": "search_guidelines",
         "args_summary": "SGLT2i / GLP-1 RA intensification",
         "result_summary": f"{len(hits)} passages"},
        {"agent": "action_agent", "tool": "draft_recall",
         "args_summary": f"{panel['total']} patients, priority-ordered",
         "result_summary": f"draft {item['id']} → pending approval"},
    ]
    async for e in _steps(ev):
        yield e
    tier_rows = [{"tier": r["group"], "patients": r["value"]} for r in panel["by_tier"]]
    net_word = "positive" if sim["net_benefit_qar"] > 0 else "negative"
    answer = f"""**{panel['total']} type 2 patients** have an HbA1c of 8% or more with obesity or kidney disease and are **not on an SGLT2 inhibitor or GLP-1 receptor agonist**, the largest treatment gap in the registry.

**What closing it is worth (counterfactual, 24 months):** the deterioration model re-scored all {sim['eligible_patients']} eligible patients with therapy applied, **{sim['relative_risk_reduction_pct']}% relative risk reduction**, ≈**{sim['expected_events_avoided']:.0f} deterioration events avoided**, {_fmt_qar(sim['event_cost_avoided_qar'])} of episode cost avoided against {_fmt_qar(sim['programme_cost_qar'])} of therapy cost → **net {_fmt_qar(sim['net_benefit_qar'])}** ({net_word} on cost alone; the clinical benefit is the case).

The national guideline recommends adding one of these agents when HbA1c remains above target on metformin, with preference for an SGLT2 inhibitor in kidney disease (see citation).

**Drafted for approval:** a priority-ordered review list for the full gap cohort is in the queue (`{item['id']}`).
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar", "title": "Intensification gap by registry risk tier",
                       "data": tier_rows, "xKey": "tier",
                       "yKeys": [{"key": "patients", "label": "Patients"}]}],
           "citations": [{"doc": h["doc"], "file": h["file"], "page": h["page"],
                          "snippet": h["snippet"]} for h in hits],
           "actions": [{"draft_id": item["id"], "tool": "draft_recall",
                        "status": "pending_human_approval"}],
           "usage": None, "model": "scripted·live-data"}


async def sc_screening_recall(persona: str):
    s_ = hie.summary()
    overdue = s_[s_["retinal_screening_overdue"] == 1]
    by_fac = (overdue.groupby("facility_name").size().sort_values(ascending=False))
    hits = rag.search("annual dilated retinal examination diabetic retinopathy screening interval", 2)
    worst_fac = by_fac.index[0]
    pids = overdue[overdue["facility_name"] == worst_fac].sort_values("hba1c_latest", ascending=False)["patient_id"].head(40).tolist()
    item = queue_service.add_draft(
        "recall_campaign", f"Retinal screening recall, {worst_fac} ({len(pids)} patients)",
        f"Recall for annual dilated retinal examination; {int(by_fac.iloc[0])} patients at {worst_fac} are overdue. "
        "Highest HbA1c first; combine with the foot exam where also overdue.", patient_ids=pids,
        citation=f"{hits[0]['doc']}, p.{hits[0]['page']}" if hits else "")
    audit_svc.log("HITL·DRAFT", "action_agent",
                  f"Retinal screening recall drafted for {worst_fac}", severity="action")
    ev = [
        {"agent": "pophealth_agent", "tool": "find_care_gaps", "args_summary": "gap_key=retinal_screening_overdue",
         "result_summary": f"{len(overdue)} patients overdue"},
        {"agent": "cohort_agent", "tool": "groupby_aggregate", "args_summary": "overdue by facility",
         "result_summary": f"{len(by_fac)} facilities; worst {worst_fac}"},
        {"agent": "guideline_agent", "tool": "search_guidelines",
         "args_summary": "retinal screening interval", "result_summary": f"{len(hits)} passages"},
        {"agent": "action_agent", "tool": "draft_recall",
         "args_summary": f"{len(pids)} patients at {worst_fac}",
         "result_summary": f"draft {item['id']} → pending approval"},
    ]
    async for e in _steps(ev):
        yield e
    both = int(((s_["retinal_screening_overdue"] == 1) & (s_["foot_exam_overdue"] == 1)).sum())
    rows = "\n".join(f"| {fac.replace(' Health Center', ' HC')} | {n} | {overdue[overdue['facility_name']==fac]['hba1c_latest'].mean():.1f}% |"
                     for fac, n in by_fac.head(5).items())
    answer = f"""**{len(overdue):,} of {len(s_):,} patients ({len(overdue)/len(s_)*100:.0f}%) are overdue for retinal screening**, and {both} of them are also overdue for a foot examination.

**Where the backlog sits:**

| Facility | Overdue | Mean HbA1c of the overdue |
|---|---|---|
{rows}

The national guideline calls for a dilated retinal examination at diagnosis and at least annually thereafter, more often when retinopathy is present (see citation).

**Drafted for approval:** a recall campaign for the {len(pids)} highest-HbA1c overdue patients at {worst_fac} is in the queue (`{item['id']}`). The remaining facilities can be drafted on request.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar", "title": "Retinal screening overdue: by facility",
                       "data": [{"facility": f.replace(" Health Center", "").replace(" Hospital", " H."), "patients": int(n)}
                                for f, n in by_fac.head(10).items()],
                       "xKey": "facility", "yKeys": [{"key": "patients", "label": "Patients overdue"}]}],
           "citations": [{"doc": h["doc"], "file": h["file"], "page": h["page"],
                          "snippet": h["snippet"]} for h in hits],
           "actions": [{"draft_id": item["id"], "tool": "draft_recall",
                        "status": "pending_human_approval"}],
           "usage": None, "model": "scripted·live-data"}


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
    fac_map = geo.map_spec(None, "pct_controlled", "Where control is won and lost, % well-controlled by facility",
                           highlight=[f["facility_name"] for f in flagged])
    answer = f"""**National glycaemic picture**, {kpi['patients']:,} patients in the diabetes registry ({kpi['pct_type1']}% type 1).

Mean HbA1c is **{kpi['mean_hba1c']}%** ({'down' if yoy<0 else 'up'} {abs(yoy):.2f} percentage points year-on-year). **{kpi['pct_well_controlled']}%** of patients are well-controlled (<7%) and **{kpi['pct_poorly_controlled']}%** are poorly controlled (≥9%).

**Facility spread:** control ranges from **{fac[-1]['pct_controlled']:.0f}%** ({fac[-1]['facility_name']}) to **{fac[0]['pct_controlled']:.0f}%** ({fac[0]['facility_name']}). {len(flagged)} facilities are below the flag line, {', '.join(f['facility_name'] for f in flagged[:3])}. That spread is an operational lever.

**Complication burden:** {kpi['pct_retinopathy']}% of patients have retinopathy, {kpi['pct_neuropathy']}% neuropathy and {kpi['pct_ckd']}% chronic kidney disease; {kpi['pct_on_sglt2_glp1']}% are on an SGLT2 inhibitor or GLP-1 receptor agonist.

**Geography:** the map shows control concentrated in Doha. The flagged facilities are in the north (Al Shamal, Al Khor) and around the Industrial Area (Hazm Mebaireek), where the expatriate workforce lives, distance from the capital and the access gradient follow the same line.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [
               fac_map,
               {"type": "line", "title": "National mean HbA1c: 36 months",
                "data": [{"month": t["month"], "HbA1c": t["mean_hba1c"]} for t in trend],
                "xKey": "month", "yKeys": [{"key": "HbA1c", "label": "Mean HbA1c %"}]},
               {"type": "bar", "title": "Facility benchmark: % well-controlled",
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
    answer = f"""**Total annual cost: {_fmt_qar(cc['total_annual_cost_qar'])}**, and it is heavily concentrated: the top 10% of patients drive **{cc['top10pct_share_pct']}%** of all spend.

**The four population segments (KMeans over cost, model risk, age, gaps, admissions):**

| Segment | Patients | Mean cost | Mean 12-mo risk | Mean gaps |
|---|---|---|---|---|
{seg_rows}

The '{segs[0]['segment']}' segment is where case-management pays for itself; the '{[x for x in segs if 'gap' in x['segment'].lower()][0]['segment'] if any('gap' in x['segment'].lower() for x in segs) else segs[1]['segment']}' segment is cheap to fix, its cost is future, not current.
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
    sims = [ml.simulate_policy(k, 24) for k in ml.INTERVENTIONS]
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
    best = max(sims, key=lambda x: x["net_benefit_qar"]); worst = min(sims, key=lambda x: x["net_benefit_qar"])
    most_events = max(sims, key=lambda x: x["expected_events_avoided"])
    answer = f"""**Programme simulation, five candidate programmes, 24-month horizon.** Every eligible patient is re-scored through the deployed deterioration model with the programme applied; the figures are computed, not assumed.

| Programme | Eligible | Relative risk reduction | Events avoided | Programme cost | Net benefit |
|---|---|---|---|---|---|
{rows}

**All five combined: ≈{comb['expected_events_avoided']:.0f} deterioration events avoided and a net {_fmt_qar(comb['net_benefit_qar'])}** over 24 months (episodes costed at QAR {ml.EVENT_COST_QAR:,}).

**Reading the table:** {best['label'].split(':')[0]} delivers the largest net benefit; {most_events['label'].split(':')[0].lower()} avoids the most events. {worst['label'].split(':')[0]} does not pay back within 24 months on cost alone, its case rests on clinical outcomes, which this model does not price. On Google Cloud the same simulation is BigQuery `ML.PREDICT` over the counterfactual cohort.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar",
                       "title": "Net benefit by programme (24 months)",
                       "data": [{"intervention": s["intervention"].replace("_program", "").replace("_", " "),
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
    answer = f"""**The equity gap is real and measurable.** Mean HbA1c ranges from **{best['mean_hba1c']}%** ({best['nationality']}) to **{worst['mean_hba1c']}%** ({worst['nationality']}), a {worst['mean_hba1c']-best['mean_hba1c']:.2f}pp spread, and control rates follow the same gradient.

The pattern tracks healthcare access, not biology: the largest gaps sit in expatriate worker populations ({', '.join(e['nationality'] for e in eq[:3])}), who also carry more open care gaps per patient. A multilingual outreach programme (SMS in Bengali, Nepali, Urdu, Tagalog) is the cheapest intervention on the board and aligns directly with the National Health Strategy's equity pillar.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar", "title": "Mean HbA1c by nationality",
                       "subtitle": "Diabetes cohort, the access gradient",
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
    answer = f"""**Ambulatory demand will grow ≈{fc['yoy_growth_pct']}% over the next 12 months**, from an average of {hist_avg:,.0f} visits/month to a peak of **{peak['visits']:,} in {peak['month']}**.

The model (trend + month-of-year seasonality over 36 months of encounter history) captures the recurring summer dip and Ramadan pattern, so the growth figure is structural, not seasonal noise. Capacity planning should target the Q4 ramp.

On Google Cloud this question is one SQL call: `AI.FORECAST` in BigQuery, powered by the TimesFM foundation model, with no training step.
"""
    data = ([{"month": h["month"], "Actual": h["visits"]} for h in fc["history"]]
            + [{"month": f["month"], "Forecast": f["visits"], "lo": f["lo"], "hi": f["hi"]}
               for f in fc["forecast"]])
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "line", "title": "Monthly ambulatory visits: history & 12-month forecast",
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
        return "met" if m["met"] else f"not met, {m['gap_patients']} patients"
    rows = "\n".join(
        f"| {m['measure_id']} | {m['name'][:44]} | **{m['rate_pct']}%** | {m['target_pct']}% "
        f"| {status_cell(m)} |" for m in measures)
    short = sorted([m for m in measures if not m["met"]],
                   key=lambda m: -(abs(m["rate_pct"] - m["target_pct"])))[:2]
    focus = " and ".join(f"{m['name'].split(' (')[0].lower()} ({m['rate_pct']}% vs a {m['target_pct']}% target)" for m in short)
    n_pat = hie.cohort_stats()["patients"]
    answer = f"""**Diabetes quality scorecard**, {len(measures)} measures computed live for {n_pat:,} patients by the population-health MCP server:

| Measure | Description | Rate | Target | Status |
|---|---|---|---|---|
{rows}

The measures furthest from target are {focus}. Each unmet measure is available as a patient-level work list.
"""
    yield {"type": "final", "answer": answer, "trace": _trace(ev),
           "charts": [{"type": "bar", "title": "Quality measures: rate vs target",
                       "data": [{"measure": m["measure_id"], "rate": m["rate_pct"],
                                 "target": m["target_pct"]} for m in measures],
                       "xKey": "measure",
                       "yKeys": [{"key": "rate", "label": "Current rate %"},
                                 {"key": "target", "label": "Target %"}]}],
           "citations": [], "actions": [], "usage": None, "model": "scripted·live-data"}


SCENARIOS = {
    "clinician": [
        {"id": "c_briefing", "tag": "C1", "label": "Morning panel briefing",
         "question": "Give me my morning briefing: review the panel and tell me who needs attention today.",
         "runner": sc_morning_briefing},
        {"id": "c_deepdive", "tag": "C2", "label": "Patient review + draft prescription",
         "question": "Review my highest-risk patient whose HbA1c is rising on metformin alone: summarise, score the risk, check the guideline, and draft what is needed.",
         "runner": sc_patient_deepdive},
        {"id": "c_intensify", "tag": "C3", "label": "Treatment intensification gap",
         "question": "How many type 2 patients with HbA1c above 8% are not on an SGLT2 inhibitor or GLP-1 agonist, what is closing that gap worth, and draft the review list.",
         "runner": sc_intensification_gap},
        {"id": "c_screening", "tag": "C4", "label": "Retinal screening recall",
         "question": "Which patients are overdue for retinal screening, where is the backlog, and draft the recall.",
         "runner": sc_screening_recall},
    ],
    "executive": [
        {"id": "e_national", "tag": "E1", "label": "National glycaemic picture",
         "question": "Give me the national glycaemic picture: trend, control rates, and facility spread.",
         "runner": sc_national_picture},
        {"id": "e_cost", "tag": "E2", "label": "Cost concentration & segments",
         "question": "Where is our spend concentrated, and what do the population segments look like?",
         "runner": sc_cost},
        {"id": "e_sim", "tag": "E3", "label": "Programme simulation (ML)",
         "question": "Simulate our five candidate programmes over 24 months and rank them by net benefit.",
         "runner": sc_policy_sim},
        {"id": "e_equity", "tag": "E4", "label": "Equity analysis",
         "question": "Show me the equity picture: outcomes by nationality.",
         "runner": sc_equity},
        {"id": "e_forecast", "tag": "E5", "label": "Demand forecast",
         "question": "Forecast outpatient demand for the next 12 months.",
         "runner": sc_forecast},
        {"id": "e_quality", "tag": "E6", "label": "Diabetes quality scorecard (MCP)",
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
