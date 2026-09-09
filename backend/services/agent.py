"""
Nabd — the multi-agent system (Google Agent Development Kit).

A supervisor LlmAgent (Gemini) orchestrates five specialists, each wrapped as an
AgentTool so every hop is visible in the event stream and rendered as a trace:

  cohort_agent      structured queries over the HIE (the fhir/BigQuery stand-in)
  guideline_agent   grounded RAG over national clinical guidelines (with citations)
  risk_agent        the deployed ML models: scoring, explanation, similarity, forecast
  pophealth_agent   ★ Google's missing piece — our population-health MCP server,
                    connected over stdio via ADK McpToolset (a REAL MCP client hop)
  action_agent      human-in-the-loop drafts (never writes to the EMR)

The supervisor additionally owns `render_chart`, emitting chart specs the UI draws.

`stream_chat` yields NDJSON events (live steps → final payload) consumed by the
frontend, so the audience watches the agents work in real time.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncGenerator

from services import audit, hie, ml, rag
from services import queue_service

BACKEND_DIR = str(Path(__file__).resolve().parent.parent)

from services import llm_client as LC
from services import platform as P

_KEY = P.API_KEY   # kept for readability; LC.llm_available() is the source of truth

# Preference order. IDs shift monthly, so we verify against what THIS key can see.
PREFERRED_MODELS = [
    "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
    "gemini-3.1-flash", "gemini-2.5-flash",
]
FALLBACK_MODEL = "gemini-2.5-flash"
MODEL_CANDIDATES = [m for m in [os.getenv("MODEL", "").strip() or None, *PREFERRED_MODELS] if m]

# How the model was chosen — surfaced on /api/health and in the deploy log so a wrong
# key or an invisible model is obvious before demo day.
RESOLUTION: dict = {"model": None, "source": None, "visible": [], "error": None}


def llm_enabled() -> bool:
    return LC.llm_available()


def _version_key(name: str) -> tuple:
    m = re.search(r"gemini-(\d+)(?:\.(\d+))?", name)
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)


@lru_cache(maxsize=1)
def resolve_model() -> str:
    """Pick the newest Gemini Flash this key can actually see.

    Order: explicit MODEL env → first preferred ID present in models.list() → newest
    visible non-lite Flash → unverified fallback (logged loudly)."""
    pinned = os.getenv("MODEL", "").strip()
    if pinned:
        RESOLUTION.update(model=pinned, source="env MODEL (unverified pin)")
        return pinned
    if not LC.llm_available():
        RESOLUTION.update(model=PREFERRED_MODELS[0], source="scripted mode (no key)")
        return PREFERRED_MODELS[0]
    try:
        client = LC.make_client()
        visible = []
        for m in client.models.list():
            name = (m.name or "").split("/")[-1]
            actions = getattr(m, "supported_actions", None) or []
            if name.startswith("gemini") and (not actions or "generateContent" in actions):
                visible.append(name)
        RESOLUTION["visible"] = visible
        for cand in PREFERRED_MODELS:
            if cand in visible:
                RESOLUTION.update(model=cand, source="verified via models.list")
                return cand
        flash = [n for n in visible if "flash" in n and not any(
            x in n for x in ("lite", "image", "tts", "live", "audio", "native", "exp", "thinking", "8b"))]
        if flash:
            best = max(flash, key=lambda n: (_version_key(n), "preview" not in n, len(n) * -1))
            RESOLUTION.update(model=best, source="newest visible Flash")
            return best
        RESOLUTION["error"] = f"none of {PREFERRED_MODELS} visible; saw {visible[:12]}"
    except Exception as e:
        RESOLUTION["error"] = f"{type(e).__name__}: {str(e)[:300]}"
    if P.VERTEX:      # Vertex lists publisher models differently; let the self-test verify and fall back
        RESOLUTION.update(model=PREFERRED_MODELS[0], source="Vertex AI — verified by self-test")
        return PREFERRED_MODELS[0]
    RESOLUTION.update(model=FALLBACK_MODEL, source="UNVERIFIED fallback — check the key")
    return FALLBACK_MODEL


def is_model_missing(e: Exception) -> bool:
    """404 / NOT_FOUND for the *model* — never for credentials or other 'not found' text."""
    code = getattr(e, "code", None)
    msg = str(e)
    if code == 404 or "NOT_FOUND" in msg:
        return True
    return bool(re.search(r"(publisher )?model[^.\n]{0,80}(not found|does not exist|is not supported|not available)", msg, re.I))


THINKING_LEVEL = (os.getenv("THINKING_LEVEL", "LOW").strip().upper() or "LOW")


def generation_config(model: str):
    """Per-hop generation settings. Gemini 3.x thinks at HIGH by default, which costs
    5–15 s of first-token latency on every one of the ~4–8 LLM calls a question needs.
    Tool routing and summarising need LOW. Override with THINKING_LEVEL=MEDIUM|HIGH."""
    from google.genai import types as gtypes
    if model.startswith("gemini-3"):
        return gtypes.GenerateContentConfig(
            thinking_config=gtypes.ThinkingConfig(thinking_level=THINKING_LEVEL))
    if "2.5" in model:                      # 2.5 uses budgets, not levels
        return gtypes.GenerateContentConfig(thinking_config=gtypes.ThinkingConfig(thinking_budget=0))
    return None


# The model actually serving traffic. Starts as resolve_model(); moves down the preference
# list when Gemini answers 503/429 ("high demand") so the demo never stalls on one model.
_active: dict = {"model": None, "switches": []}


def active_model() -> str:
    if _active["model"] is None:
        _active["model"] = resolve_model()
    return _active["model"]


def fallback_candidates(current: str) -> list[str]:
    visible = RESOLUTION.get("visible") or []
    order = [m for m in PREFERRED_MODELS if (not visible or m in visible)] or PREFERRED_MODELS
    burnt = {current} | {x["from"] for x in _active["switches"]} | {x["to"] for x in _active["switches"]}
    return [m for m in order if m not in burnt]


def is_capacity_error(e: Exception) -> bool:
    code = getattr(e, "code", None) or getattr(getattr(e, "status", None), "code", None)
    msg = str(e)
    if isinstance(e, (StallError, asyncio.TimeoutError, TimeoutError)):
        return True
    return code in (429, 500, 502, 503, 504) or any(
        k in msg for k in ("UNAVAILABLE", "RESOURCE_EXHAUSTED", "high demand", "overloaded", " 503", " 429"))


def switch_model(reason: str) -> str | None:
    cur = active_model()
    nxt = next(iter(fallback_candidates(cur)), None)
    if nxt:
        _active["model"] = nxt
        _active["switches"].append({"from": cur, "to": nxt, "reason": reason[:160], "at": time.time()})
        print(f"⚠ Gemini capacity error on {cur} — switching to {nxt}: {reason[:160]}", flush=True)
    return nxt


HTTP_TIMEOUT_MS = int(os.getenv("GEMINI_HTTP_TIMEOUT_MS", "45000"))   # per HTTP request
STALL_SECONDS = float(os.getenv("AGENT_STALL_SECONDS", "40"))          # no event from the graph
TURN_DEADLINE_SECONDS = float(os.getenv("AGENT_TURN_DEADLINE_SECONDS", "150"))


class StallError(RuntimeError):
    """The agent graph produced no event for STALL_SECONDS — treated like a capacity error."""


def _retry_options():
    from google.genai import types as gtypes
    return gtypes.HttpRetryOptions(attempts=3, initial_delay=1.0, max_delay=4.0, exp_base=2.0,
                                   jitter=0.3, http_status_codes=[429, 500, 502, 503, 504])


def _http_options():
    from google.genai import types as gtypes
    return gtypes.HttpOptions(timeout=HTTP_TIMEOUT_MS, retry_options=_retry_options())


def _llm(model: str):
    """ADK Gemini connection with a hard HTTP timeout and client-side retries on 429/5xx.
    Without the timeout a stalled streaming response during a 'high demand' incident
    hangs the turn forever; ADK's own client sets none."""
    from functools import cached_property
    from google.adk.models.google_llm import Gemini
    from google.genai import Client

    class NabdGemini(Gemini):
        @cached_property
        def api_client(self) -> Client:                       # noqa: D401 — ADK hook
            return LC.make_client(http_options=_http_options())

    return NabdGemini(model=model, retry_options=_retry_options())


def self_test(model: str | None = None) -> dict:
    """One real generate_content call so the deploy log proves key + model work.
    Retries transient capacity errors and, if a model is saturated, moves to the next."""
    if not LC.llm_available():
        return {"ok": False, "skipped": "no key"}
    client = LC.make_client(http_options=_http_options())
    tried = []
    model = model or active_model()
    while True:
        t0 = time.time()
        try:
            r = client.models.generate_content(model=model, contents="Reply with the single word OK.",
                                               config=generation_config(model))
            text = (r.text or "").strip()
            return {"ok": bool(text), "model": model, "reply": text[:40],
                    "ms": int((time.time() - t0) * 1000), "tried": tried or None}
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:300]}"
            tried.append({"model": model, "error": err})
            if is_capacity_error(e) or is_model_missing(e):
                nxt = switch_model(err)
                if nxt:
                    model = nxt
                    continue
            return {"ok": False, "model": model, "error": err, "ms": int((time.time() - t0) * 1000),
                    "tried": tried, "capacity": is_capacity_error(e)}


# ─────────────────────────── function tools ───────────────────────────
# Complex arguments travel as JSON strings — maximally robust for function calling.

def describe_dataset() -> dict:
    """List every HIE table with row counts, descriptions and columns. Call this FIRST
    whenever you are unsure which column or table holds something."""
    return hie.describe_dataset()


def query_bigquery(sql: str) -> dict:
    """Run ONE read-only GoogleSQL SELECT against the national HIE in BigQuery (dataset
    nabd_hie; tables: patient_summary, patients, conditions, observations, medications,
    encounters, care_gaps, facilities — unqualified names resolve to the dataset). Use it
    for aggregations, joins or window functions the other tools cannot express. Rows are
    capped at 200 and bytes billed are capped; the job id and bytes processed are returned."""
    from services import bq
    out = bq.query(sql)
    audit.log("BQ·QUERY", "cohort_agent", f"{out.get('bytes_processed', 0):,} B · "
              f"{out.get('row_count', 0)} rows · {out.get('ms', 0)} ms · {sql[:120]}")
    return out


def describe_column(column: str, table: str = "patient_summary") -> dict:
    """Summary statistics for one column (numeric: mean/quartiles; categorical: top values)."""
    return hie.describe_column(column, table)


def get_patient(patient_id: str) -> dict:
    """Full record for one patient: summary, conditions, active medications, recent
    encounters. Respects HIE consent — restricted patients return a denial."""
    res = hie.get_patient(patient_id)
    if res.get("consent") == "DENIED":
        audit.log("CONSENT·DENY", "cohort_agent",
                  f"Access to {patient_id} blocked — restricted consent", patient_id, "warning")
    else:
        audit.log("FHIR·READ", "cohort_agent", f"Patient record read: {patient_id}", patient_id)
    return res


def patient_timeline(patient_id: str, obs_keys_json: str = "") -> dict:
    """Longitudinal labs/vitals for one patient (for trends). obs_keys_json is an optional
    JSON list from: hba1c,fpg,sbp,dbp,ldl,hdl,tg,egfr,acr,bmi,ef."""
    keys = json.loads(obs_keys_json) if obs_keys_json else None
    return hie.patient_timeline(patient_id, keys)


def filter_cohort(filters_json: str, select_columns_json: str = "",
                  aggregate_json: str = "", limit: int = 20) -> dict:
    """Filter the patient_summary table. filters_json: JSON list of {column, op, value};
    ops: ==,!=,>,<,>=,<=,between,contains,not_contains,in,not_in,is_null,not_null.
    aggregate_json (optional): {"column":...,"func":"mean|median|sum|min|max|std"}.
    select_columns_json (optional): JSON list of columns to return per patient."""
    return hie.filter_cohort(
        json.loads(filters_json) if filters_json else [],
        select_columns=json.loads(select_columns_json) if select_columns_json else None,
        aggregate=json.loads(aggregate_json) if aggregate_json else None,
        limit=limit)


def groupby_aggregate(group_by: str, metric: str = "", func: str = "mean",
                      filters_json: str = "", top: int = 30) -> dict:
    """Group patients by a column and aggregate a metric (e.g. mean hba1c_latest by
    facility_name). Empty metric = patient counts."""
    return hie.groupby_aggregate(group_by, metric or None, func,
                                 json.loads(filters_json) if filters_json else None, top)


def top_n(sort_by: str, n: int = 10, ascending: bool = False,
          filters_json: str = "", select_columns_json: str = "") -> dict:
    """Top/bottom N patients by a column (e.g. annual_cost_qar, hba1c_latest, adherence_pdc)."""
    return hie.top_n(sort_by, n, ascending,
                     json.loads(filters_json) if filters_json else None,
                     json.loads(select_columns_json) if select_columns_json else None)


def correlate(col_a: str, col_b: str) -> dict:
    """Pearson correlation between two numeric patient_summary columns."""
    return hie.correlate(col_a, col_b)


def histogram(column: str, bins: int = 10, filters_json: str = "") -> dict:
    """Binned distribution of a numeric column."""
    return hie.histogram(column, bins, json.loads(filters_json) if filters_json else None)


def cohort_kpis() -> dict:
    """Headline registry KPIs: size, control rates, CVD prevalence, gaps, cost."""
    return hie.cohort_stats()


def facility_benchmark() -> dict:
    """Per-facility benchmark: patients, mean HbA1c, % controlled, gaps, cost, status."""
    return {"rows": hie.facility_benchmark()}


def equity_breakdown() -> dict:
    """Outcomes by nationality — the health-equity view (control %, HbA1c, gaps, cost)."""
    return {"rows": hie.equity_breakdown()}


def search_guidelines(query: str, top_k: int = 4) -> dict:
    """Search the national clinical guideline corpus (diabetes, CKD, hypertension,
    lipids, heart failure, CV prevention). Returns cited passages with document + page.
    ALWAYS use before making any clinical recommendation."""
    hits = rag.search(query, top_k)
    audit.log("RAG·SEARCH", "guideline_agent", f"Guideline search: '{query[:80]}'")
    return {"hits": hits}


def score_patient_risk(patient_id: str) -> dict:
    """Score one patient through the deployed XGBoost complication-risk model.
    Returns 12-month event probability, model risk band, and SHAP-style top drivers."""
    res = ml.score_patient(patient_id)
    audit.log("ML·SCORE", "risk_agent",
              f"complication_risk v1.2.0 scored {patient_id}", patient_id)
    return res


def stratify_cohort_risk(filters_json: str = "", top_n: int = 10) -> dict:
    """Score a whole cohort through the risk model: band distribution, expected events,
    highest-risk patients. Empty filters = whole registry."""
    return ml.stratify_cohort(json.loads(filters_json) if filters_json else None, top_n)


def similar_patients(patient_id: str, k: int = 6) -> dict:
    """Find the k most clinically similar patients (standardised feature space) and
    what treatments/control they have — 'patients like this one'."""
    return ml.similar_patients(patient_id, k)


def simulate_policy(intervention: str, horizon_months: int = 12) -> dict:
    """Counterfactual policy what-if by re-scoring the eligible cohort through the risk
    model with the programme applied. intervention: sglt2_glp1_intensification |
    hba1c_recall_program | adherence_support_program | bp_control_program |
    renal_protection_program | combined."""
    res = ml.simulate_policy(intervention, horizon_months)
    audit.log("ML·SIMULATE", "risk_agent",
              f"Counterfactual simulation: {intervention} over {horizon_months}m")
    return res


def simulate_patient_whatif(patient_id: str, overrides_json: str = "") -> dict:
    """What-if for ONE patient: change levers and re-score through the deployed deterioration
    model. overrides_json is a JSON object of lever -> value, e.g.
    {"hba1c_latest": 8.0, "on_sglt2_glp1": 1, "adherence_pdc": 0.9, "sbp_latest": 130}.
    Levers: hba1c_latest, hba1c_days_since_test, sbp_latest, egfr_latest, acr_latest,
    adherence_pdc, bmi, smoker, on_metformin, on_sglt2_glp1, on_raas_inhibitor,
    admissions_12mo, ed_visits_12mo. Returns baseline vs simulated probability, band,
    registry percentile, per-feature attribution, care gaps closed and the expected cost delta."""
    from services import whatif
    return whatif.tool_simulate(patient_id, overrides_json)


def visit_forecast() -> dict:
    """12-month ambulatory demand forecast (monthly, with 80% interval) from the
    seasonal model over 36 months of encounter history."""
    return ml.visit_forecast()


def model_cards() -> dict:
    """Governance cards for every deployed model: version, framework, training data,
    metrics (AUC vs the legacy registry score), intended use, limitations."""
    return {"models": ml.model_cards()}


def render_chart(spec_json: str) -> dict:
    """Emit a chart for the UI. spec_json is a JSON object:
    {"type":"bar|line|area|pie|scatter","title":...,"subtitle":...,
     "data":[{...row objects...}],"xKey":...,"yKeys":[{"key":...,"label":...}],
     "stacked":false,"yAxisLabel":...,"footnote":...}
    Use whenever the user asks to see/plot/compare data, or a chart would clearly help.
    Keep data ≤ 24 rows. You must STILL narrate the finding in words."""
    try:
        spec = json.loads(spec_json)
    except Exception as e:
        return {"ok": False, "error": f"invalid chart spec JSON: {e}"}
    return {"ok": True, "chart": spec}


def render_map(metric: str = "pct_controlled", facility_names_json: str = "",
               title: str = "", highlight_json: str = "") -> dict:
    """Emit a colour-coded FACILITY MAP of Qatar for the UI. metric: pct_controlled |
    gaps_per_100 | hba1c_overdue | mean_risk_pct | mean_cost | mean_hba1c.
    facility_names_json: optional JSON list of facility names to include (empty = all 18).
    highlight_json: optional JSON list of facility names to ring-highlight.
    Use whenever the user asks about facilities, regions, geography, or 'where'."""
    from services import geo
    names = json.loads(facility_names_json) if facility_names_json else None
    hl = json.loads(highlight_json) if highlight_json else None
    return {"ok": True, "chart": geo.map_spec(names, metric, title or None, hl)}


def draft_prescription(patient_id: str, drug: str, dose: str, rationale: str,
                       citation: str = "") -> dict:
    """Draft a prescription for HUMAN clinician approval. It is queued, never submitted."""
    item = queue_service.add_draft("prescription", f"{drug} {dose}".strip(), rationale,
                                   patient_id=patient_id, citation=citation)
    audit.log("HITL·DRAFT", "action_agent",
              f"Prescription draft {drug} {dose} for {patient_id} → approval queue",
              patient_id, "action")
    return {"ok": True, "draft_id": item["id"], "status": "pending_human_approval"}


def draft_recall(patient_ids_json: str, reason: str, channel: str = "sms") -> dict:
    """Draft a recall/outreach campaign (sms|call|letter) for a list of patients —
    queued for human approval."""
    pids = json.loads(patient_ids_json)
    item = queue_service.add_draft("recall_campaign", f"Recall {len(pids)} patients ({channel})",
                                   reason, patient_ids=pids)
    audit.log("HITL·DRAFT", "action_agent",
              f"Recall campaign drafted for {len(pids)} patients → approval queue",
              severity="action")
    return {"ok": True, "draft_id": item["id"], "patients": len(pids),
            "status": "pending_human_approval"}


def draft_referral(patient_id: str, specialty: str, rationale: str) -> dict:
    """Draft a specialist referral (e.g. cardiology, nephrology, ophthalmology) —
    queued for human approval."""
    item = queue_service.add_draft("referral", f"Referral → {specialty}", rationale,
                                   patient_id=patient_id)
    audit.log("HITL·DRAFT", "action_agent",
              f"Referral to {specialty} drafted for {patient_id}", patient_id, "action")
    return {"ok": True, "draft_id": item["id"], "status": "pending_human_approval"}


# ─────────────────────────── agent graph ───────────────────────────

SUPERVISOR_INSTRUCTION = """You are Nabd (نبض) — the national population-health AI assistant operating on top of the Health Information Exchange for the national diabetes registry: 4,000 people living with type 1 or type 2 diabetes, their complications (retinopathy, neuropathy, kidney disease), therapy, adherence and utilisation.

You serve two personas (the user message states which):
- CLINICIAN: point-of-care decision support. Be clinically precise and concise.
- EXECUTIVE: population insight — benchmarking, cost, equity, policy. Lead with the number that matters.

You are a SUPERVISOR of specialist agents, each exposed as a tool:
- cohort_agent: ANY question needing patient or population data (counts, filters, group-bys, rankings, correlations, patient records, timelines, facility/equity views). It queries the HIE directly — never invent figures.
- guideline_agent: national clinical guideline retrieval. MANDATORY before any clinical recommendation; cite document + page.
- risk_agent: the deployed ML models — patient risk scoring with explanations, cohort stratification, similar patients, demand forecast, counterfactual policy simulation, model cards.
- pophealth_agent: population-health MCP tools — quality measures, care gaps, cohort building, risk stratification, policy simulation, and drafting population interventions. Prefer it for care-gap / quality-measure / campaign questions.
- action_agent: draft prescriptions, recalls, referrals. Drafts ALWAYS go to the human approval queue — never present a clinical action as done.

You also own render_chart (charts) and render_map (a colour-coded facility map of Qatar): call them whenever the user asks to see/plot/compare data, or asks about facilities/regions/geography. Keep chart data compact (≤24 rows).

Rules:
1. Route to specialists for facts; never fabricate numbers, patient data, or citations.
2. Delegate with a specific, self-contained request (the specialist has no chat context).
3. For clinical recommendations: guideline citation (document + page) is mandatory.
4. Lead the final answer with the direct result and its actual numbers; then brief supporting detail. Clean markdown, short sentences, bold the key figures.
5. Never end on a filler line like "let me check" — always finish with the complete written answer. Charts support the text; they never replace it.
6. Population aggregates are fine to show; do not expose row-level data for restricted-consent patients (the tools enforce this — surface the denial transparently when it happens).
"""

_runners: dict = {}
_session_service = None


def _build_tools_map(model_name: str | None = None):
    from google.adk.agents import LlmAgent
    from google.adk.tools import AgentTool
    from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
    from mcp import StdioServerParameters

    model = model_name or active_model()
    gen_cfg = generation_config(model)
    llm = _llm(model)

    cohort_agent = LlmAgent(
        name="cohort_agent", model=llm, generate_content_config=gen_cfg,
        description=("Queries the national HIE: patient records, timelines, cohort filters, "
                     "group-bys, rankings, correlations, facility benchmark, equity view, KPIs."),
        instruction=("You are the HIE data specialist. Use your tools to answer the request "
                     "with REAL numbers. If unsure about columns, call describe_dataset first. "
                     + ("The exchange lives in BigQuery: prefer query_bigquery for aggregations, joins "
                        "and rankings the structured tools cannot express, and quote the bytes processed. "
                        if P.HIE_BACKEND == "bigquery" else "") +
                     "Return a compact, complete factual summary of what you found (with the "
                     "numbers); no pleasantries."),
        tools=[describe_dataset, describe_column, get_patient, patient_timeline,
               filter_cohort, groupby_aggregate, top_n, correlate, histogram,
               cohort_kpis, facility_benchmark, equity_breakdown]
              + ([query_bigquery] if P.HIE_BACKEND == "bigquery" else []))

    guideline_agent = LlmAgent(
        name="guideline_agent", model=llm, generate_content_config=gen_cfg,
        description="Retrieves and cites national clinical guideline passages (RAG).",
        instruction=("You are the clinical guideline retrieval specialist. Search the corpus, "
                     "then answer with the relevant recommendation(s) and ALWAYS cite document "
                     "name + page for each claim. Quote thresholds and doses exactly."),
        tools=[search_guidelines])

    risk_agent = LlmAgent(
        name="risk_agent", model=llm, generate_content_config=gen_cfg,
        description=("Runs the deployed ML models: risk scoring with SHAP drivers, cohort "
                     "stratification, similar patients, demand forecast, counterfactual policy "
                     "simulation, model governance cards."),
        instruction=("You are the ML specialist. Use the models — never guess. When you score, "
                     "report the probability, the band, and the top drivers in plain clinical "
                     "language. For simulations report events avoided, costs and net benefit, "
                     "and state the method in one line. For a single patient's what-if question "
                     "('what if HbA1c came down to 8', 'if we start an SGLT2 inhibitor') use "
                     "simulate_patient_whatif with the matching levers and report before/after risk, "
                     "the attribution and the gaps closed."),
        tools=[score_patient_risk, stratify_cohort_risk, similar_patients,
               simulate_policy, simulate_patient_whatif, visit_forecast, model_cards])

    pophealth_tools = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable, args=["-m", "pophealth_mcp"], cwd=BACKEND_DIR),
            timeout=30),
    )
    pophealth_agent = LlmAgent(
        name="pophealth_agent", model=llm, generate_content_config=gen_cfg,
        description=("Population-health MCP specialist: HEDIS-style quality measures, care-gap "
                     "hunting, cohort building, model-backed stratification, policy simulation, "
                     "and drafting population interventions (human-approved)."),
        instruction=("You are the population-health specialist, working through the "
                     "population-health MCP server's tools. Answer with the measure/gap/cohort "
                     "numbers you computed. When asked to act, use draft_intervention — it goes "
                     "to the human approval queue."),
        tools=[pophealth_tools])

    action_agent = LlmAgent(
        name="action_agent", model=llm, generate_content_config=gen_cfg,
        description="Drafts prescriptions, recall campaigns and referrals for human approval.",
        instruction=("You draft clinical actions. Every draft goes to the human-in-the-loop "
                     "queue — say so explicitly. Include the clinical rationale and guideline "
                     "citation when provided. Never claim an action was executed."),
        tools=[draft_prescription, draft_recall, draft_referral])

    supervisor = LlmAgent(
        name="nabd_supervisor", model=llm, generate_content_config=gen_cfg,
        description="Nabd population-health supervisor",
        instruction=SUPERVISOR_INSTRUCTION,
        tools=[AgentTool(cohort_agent), AgentTool(guideline_agent), AgentTool(risk_agent),
               AgentTool(pophealth_agent), AgentTool(action_agent), render_chart, render_map])
    return supervisor


def _get_runner(model_name: str | None = None):
    """One ADK Runner per model, sharing a session service so a mid-conversation model
    switch keeps the conversation."""
    global _session_service
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    model = model_name or active_model()
    if _session_service is None:
        _session_service = InMemorySessionService()
    if model not in _runners:
        _runners[model] = Runner(agent=_build_tools_map(model), app_name="nabd",
                                 session_service=_session_service)
    return _runners[model]


def _summarise_args(tool: str, args: dict) -> str:
    if not args:
        return tool
    parts = []
    for k, v in list(args.items())[:4]:
        s = str(v)
        parts.append(f"{k}={s[:70]}{'…' if len(s) > 70 else ''}")
    return ", ".join(parts)


def _normalise_response(resp: Any) -> Any:
    if isinstance(resp, dict) and set(resp.keys()) == {"result"}:
        resp = resp["result"]
    if isinstance(resp, str):
        try:
            return json.loads(resp)
        except Exception:
            return resp
    return resp


def _summarise_result(tool: str, resp: Any) -> str:
    r = _normalise_response(resp)
    if isinstance(r, dict):
        for key in ("matched", "patients_with_gap", "eligible_patients", "rate_pct",
                    "event_probability_12m", "draft_id", "pearson_r"):
            if key in r:
                return f"{key}: {r[key]}"
        if "hits" in r:
            return f"{len(r['hits'])} guideline passages retrieved"
        if "rows" in r and isinstance(r["rows"], list):
            return f"{len(r['rows'])} rows returned"
        if "patient" in r:
            return "patient record retrieved"
        if r.get("consent") == "DENIED":
            return "CONSENT DENIED — access blocked"
        keys = list(r.keys())[:4]
        return f"returned: {', '.join(keys)}"
    if isinstance(r, list):
        return f"{len(r)} items"
    return str(r)[:120]


async def stream_chat(message: str, session_id: str, persona: str = "clinician",
                      ) -> AsyncGenerator[dict, None]:
    """Run the multi-agent system, yielding live step events then the final payload.
    If Gemini answers 503/429 for the active model (after client retries), the request is
    re-run once on the next model in the preference list."""
    for attempt in range(3):
        model = active_model()
        try:
            async for ev in _watchdog(_stream_once(message, session_id, persona, model)):
                yield ev
            return
        except Exception as e:
            if attempt < 2 and (is_capacity_error(e) or is_model_missing(e)) and switch_model(f"{type(e).__name__}: {e}"):
                why = ("went silent" if isinstance(e, StallError) else "not available on this endpoint"
                       if is_model_missing(e) else "at capacity (503)")
                yield {"type": "reset"}
                yield {"type": "step", "status": "done", "agent": "system", "tool": "model_fallback",
                       "detail": f"{model} {why} — re-running on {active_model()}"}
                continue
            raise


async def _watchdog(agen: AsyncGenerator[dict, None]) -> AsyncGenerator[dict, None]:
    """Re-yield events; abort if the graph is silent for STALL_SECONDS or the turn exceeds
    TURN_DEADLINE_SECONDS. A hung HTTP stream must never hang the demo."""
    started = time.time()
    try:
        while True:
            remaining = TURN_DEADLINE_SECONDS - (time.time() - started)
            if remaining <= 0:
                raise StallError(f"turn exceeded {TURN_DEADLINE_SECONDS:.0f}s")
            try:
                ev = await asyncio.wait_for(agen.__anext__(), timeout=min(STALL_SECONDS, remaining))
            except StopAsyncIteration:
                return
            except asyncio.TimeoutError:
                raise StallError(f"no event from the agent graph for {STALL_SECONDS:.0f}s") from None
            yield ev
    finally:
        await agen.aclose()


async def _stream_once(message: str, session_id: str, persona: str, model: str,
                       ) -> AsyncGenerator[dict, None]:
    from google.genai import types as gtypes
    from google.adk.agents.run_config import RunConfig, StreamingMode

    runner = _get_runner(model)
    sess = await _session_service.get_session(app_name="nabd", user_id="demo",
                                              session_id=session_id)
    if sess is None:
        await _session_service.create_session(app_name="nabd", user_id="demo",
                                              session_id=session_id)

    persona_hint = {
        "clinician": "[persona: CLINICIAN — point-of-care decision support]",
        "executive": "[persona: EXECUTIVE — population health leadership]",
    }.get(persona, "")
    content = gtypes.Content(role="user", parts=[gtypes.Part(text=f"{persona_hint}\n{message}")])

    trace: list[dict] = []
    charts: list[dict] = []
    citations: list[dict] = []
    actions: list[dict] = []
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "llm_calls": 0}
    pending: dict[str, dict] = {}
    final_text = ""

    t_start = time.time()
    first_token_ms = None
    async for event in runner.run_async(user_id="demo", session_id=session_id,
                                        new_message=content,
                                        run_config=RunConfig(streaming_mode=StreamingMode.SSE)):
        author = event.author or "agent"
        if getattr(event, "partial", False):
            # Streaming chunk: surface the supervisor's prose as it is written so the
            # clinician reads while the model finishes. Everything else waits for the
            # aggregated (non-partial) event below.
            if author == "nabd_supervisor":
                for part in (event.content.parts if event.content and event.content.parts else []):
                    if getattr(part, "text", None) and not getattr(part, "thought", False):
                        if first_token_ms is None:
                            first_token_ms = int((time.time() - t_start) * 1000)
                        yield {"type": "delta", "text": part.text}
            continue
        if event.usage_metadata is not None:
            usage["prompt_tokens"] += int(event.usage_metadata.prompt_token_count or 0)
            usage["completion_tokens"] += int(event.usage_metadata.candidates_token_count or 0)
            usage["total_tokens"] += int(event.usage_metadata.total_token_count or 0)
            usage["llm_calls"] += 1
        for part in (event.content.parts if event.content and event.content.parts else []):
            fc = getattr(part, "function_call", None)
            if fc is not None:
                args = dict(fc.args or {})
                step = {"agent": author, "tool": fc.name,
                        "args_summary": _summarise_args(fc.name, args),
                        "t0": time.time()}
                pending[f"{fc.name}"] = step
                if fc.name == "render_chart":
                    try:
                        charts.append(json.loads(args.get("spec_json", "{}")))
                    except Exception:
                        pass
                yield {"type": "step", "status": "call", "agent": author, "tool": fc.name,
                       "detail": step["args_summary"]}
            fr = getattr(part, "function_response", None)
            if fr is not None:
                resp = _normalise_response(fr.response if fr.response is not None else {})
                step = pending.pop(f"{fr.name}", {"agent": author, "tool": fr.name,
                                                  "args_summary": "", "t0": time.time()})
                summary = _summarise_result(fr.name, resp)
                dur = int((time.time() - step["t0"]) * 1000)
                trace.append({"agent": step["agent"], "tool": fr.name,
                              "args_summary": step["args_summary"],
                              "result_summary": summary, "duration_ms": dur})
                if fr.name == "render_map" and isinstance(resp, dict) and resp.get("chart"):
                    charts.append(resp["chart"])
                if fr.name == "search_guidelines" and isinstance(resp, dict):
                    for h in resp.get("hits", []):
                        citations.append({"doc": h.get("doc"), "file": h.get("file"),
                                          "page": h.get("page"), "snippet": h.get("snippet")})
                if isinstance(resp, dict) and resp.get("draft_id"):
                    actions.append({"draft_id": resp["draft_id"],
                                    "tool": fr.name, "status": "pending_human_approval"})
                yield {"type": "step", "status": "done", "agent": step["agent"],
                       "tool": fr.name, "detail": summary, "duration_ms": dur}
            if getattr(part, "text", None) and event.is_final_response():
                final_text = (final_text + "\n" + part.text).strip()

    # de-dup citations
    seen, uniq = set(), []
    for c in citations:
        k = (c.get("doc"), c.get("page"))
        if k not in seen:
            seen.add(k)
            uniq.append(c)

    audit.log("AGENT·ANSWER", "nabd_supervisor",
              f"Answered ({persona}): '{message[:90]}' — {len(trace)} tool steps, "
              f"{usage['total_tokens']} tokens")
    yield {"type": "final",
           "answer": final_text or "I wasn't able to produce an answer for that query.",
           "trace": trace, "charts": charts, "citations": uniq, "actions": actions,
           "usage": {**usage, "wall_ms": int((time.time() - t_start) * 1000),
                     "first_token_ms": first_token_ms, "thinking_level": THINKING_LEVEL},
           "model": model}
