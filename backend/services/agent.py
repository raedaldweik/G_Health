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
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncGenerator

from services import audit, hie, ml, rag
from services import queue_service

BACKEND_DIR = str(Path(__file__).resolve().parent.parent)

# Accept either env name; ADK/google-genai read GOOGLE_API_KEY.
_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
if _KEY and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = _KEY
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")

MODEL_CANDIDATES = [m for m in [
    os.getenv("MODEL", "").strip() or None,
    "gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash",
] if m]


def llm_enabled() -> bool:
    return bool(_KEY)


@lru_cache(maxsize=1)
def resolve_model() -> str:
    """Pick the newest Gemini flash model this key can see — IDs shift monthly."""
    if not _KEY:
        return MODEL_CANDIDATES[0]
    try:
        from google import genai
        client = genai.Client(api_key=_KEY)
        for m in MODEL_CANDIDATES:
            try:
                client.models.get(model=m)
                return m
            except Exception:
                continue
    except Exception:
        pass
    return MODEL_CANDIDATES[-1]


# ─────────────────────────── function tools ───────────────────────────
# Complex arguments travel as JSON strings — maximally robust for function calling.

def describe_dataset() -> dict:
    """List every HIE table with row counts, descriptions and columns. Call this FIRST
    whenever you are unsure which column or table holds something."""
    return hie.describe_dataset()


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
    """Top/bottom N patients by a column (e.g. annual_cost_qar, ascvd_10yr_pct)."""
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
    model with the treatment applied. intervention: close_statin_gap |
    close_glp1_sglt2_gap | close_af_anticoag_gap | bp_control_program | combined."""
    res = ml.simulate_policy(intervention, horizon_months)
    audit.log("ML·SIMULATE", "risk_agent",
              f"Counterfactual simulation: {intervention} over {horizon_months}m")
    return res


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

SUPERVISOR_INSTRUCTION = """You are Nabd (نبض) — the national population-health AI assistant operating on top of the Health Information Exchange for a 4,000-patient cardiometabolic registry (diabetes-led, with the full cardiovascular picture).

You serve two personas (the user message states which):
- CLINICIAN: point-of-care decision support. Be clinically precise and concise.
- EXECUTIVE: population insight — benchmarking, cost, equity, policy. Lead with the number that matters.

You are a SUPERVISOR of specialist agents, each exposed as a tool:
- cohort_agent: ANY question needing patient or population data (counts, filters, group-bys, rankings, correlations, patient records, timelines, facility/equity views). It queries the HIE directly — never invent figures.
- guideline_agent: national clinical guideline retrieval. MANDATORY before any clinical recommendation; cite document + page.
- risk_agent: the deployed ML models — patient risk scoring with explanations, cohort stratification, similar patients, demand forecast, counterfactual policy simulation, model cards.
- pophealth_agent: population-health MCP tools — quality measures, care gaps, cohort building, risk stratification, policy simulation, and drafting population interventions. Prefer it for care-gap / quality-measure / campaign questions.
- action_agent: draft prescriptions, recalls, referrals. Drafts ALWAYS go to the human approval queue — never present a clinical action as done.

You also own render_chart: call it whenever the user asks to see/plot/compare data or a chart clearly helps. Keep chart data compact (≤24 rows).

Rules:
1. Route to specialists for facts; never fabricate numbers, patient data, or citations.
2. Delegate with a specific, self-contained request (the specialist has no chat context).
3. For clinical recommendations: guideline citation (document + page) is mandatory.
4. Lead the final answer with the direct result and its actual numbers; then brief supporting detail. Clean markdown, short sentences, bold the key figures.
5. Never end on a filler line like "let me check" — always finish with the complete written answer. Charts support the text; they never replace it.
6. Population aggregates are fine to show; do not expose row-level data for restricted-consent patients (the tools enforce this — surface the denial transparently when it happens).
"""

_runner = None
_session_service = None


def _build_tools_map():
    from google.adk.agents import LlmAgent
    from google.adk.tools import AgentTool
    from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
    from mcp import StdioServerParameters

    model = resolve_model()

    cohort_agent = LlmAgent(
        name="cohort_agent", model=model,
        description=("Queries the national HIE: patient records, timelines, cohort filters, "
                     "group-bys, rankings, correlations, facility benchmark, equity view, KPIs."),
        instruction=("You are the HIE data specialist. Use your tools to answer the request "
                     "with REAL numbers. If unsure about columns, call describe_dataset first. "
                     "Return a compact, complete factual summary of what you found (with the "
                     "numbers); no pleasantries."),
        tools=[describe_dataset, describe_column, get_patient, patient_timeline,
               filter_cohort, groupby_aggregate, top_n, correlate, histogram,
               cohort_kpis, facility_benchmark, equity_breakdown])

    guideline_agent = LlmAgent(
        name="guideline_agent", model=model,
        description="Retrieves and cites national clinical guideline passages (RAG).",
        instruction=("You are the clinical guideline retrieval specialist. Search the corpus, "
                     "then answer with the relevant recommendation(s) and ALWAYS cite document "
                     "name + page for each claim. Quote thresholds and doses exactly."),
        tools=[search_guidelines])

    risk_agent = LlmAgent(
        name="risk_agent", model=model,
        description=("Runs the deployed ML models: risk scoring with SHAP drivers, cohort "
                     "stratification, similar patients, demand forecast, counterfactual policy "
                     "simulation, model governance cards."),
        instruction=("You are the ML specialist. Use the models — never guess. When you score, "
                     "report the probability, the band, and the top drivers in plain clinical "
                     "language. For simulations report events avoided, costs and net benefit, "
                     "and state the method in one line."),
        tools=[score_patient_risk, stratify_cohort_risk, similar_patients,
               simulate_policy, visit_forecast, model_cards])

    pophealth_tools = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable, args=["-m", "pophealth_mcp"], cwd=BACKEND_DIR),
            timeout=30),
    )
    pophealth_agent = LlmAgent(
        name="pophealth_agent", model=model,
        description=("Population-health MCP specialist: HEDIS-style quality measures, care-gap "
                     "hunting, cohort building, model-backed stratification, policy simulation, "
                     "and drafting population interventions (human-approved)."),
        instruction=("You are the population-health specialist, working through the "
                     "population-health MCP server's tools. Answer with the measure/gap/cohort "
                     "numbers you computed. When asked to act, use draft_intervention — it goes "
                     "to the human approval queue."),
        tools=[pophealth_tools])

    action_agent = LlmAgent(
        name="action_agent", model=model,
        description="Drafts prescriptions, recall campaigns and referrals for human approval.",
        instruction=("You draft clinical actions. Every draft goes to the human-in-the-loop "
                     "queue — say so explicitly. Include the clinical rationale and guideline "
                     "citation when provided. Never claim an action was executed."),
        tools=[draft_prescription, draft_recall, draft_referral])

    supervisor = LlmAgent(
        name="nabd_supervisor", model=model,
        description="Nabd population-health supervisor",
        instruction=SUPERVISOR_INSTRUCTION,
        tools=[AgentTool(cohort_agent), AgentTool(guideline_agent), AgentTool(risk_agent),
               AgentTool(pophealth_agent), AgentTool(action_agent), render_chart])
    return supervisor


def _get_runner():
    global _runner, _session_service
    if _runner is None:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        _session_service = InMemorySessionService()
        _runner = Runner(agent=_build_tools_map(), app_name="nabd",
                         session_service=_session_service)
    return _runner


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
    """Run the multi-agent system, yielding live step events then the final payload."""
    from google.genai import types as gtypes

    runner = _get_runner()
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

    async for event in runner.run_async(user_id="demo", session_id=session_id,
                                        new_message=content):
        if event.usage_metadata is not None:
            usage["prompt_tokens"] += int(event.usage_metadata.prompt_token_count or 0)
            usage["completion_tokens"] += int(event.usage_metadata.candidates_token_count or 0)
            usage["total_tokens"] += int(event.usage_metadata.total_token_count or 0)
            usage["llm_calls"] += 1
        author = event.author or "agent"
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
           "usage": usage, "model": resolve_model()}
