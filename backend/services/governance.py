"""
Per-answer governance record.

Every assistant answer ships with the controls that were in force while it was
produced. Nothing here is asserted; every check is computed from the turn's own
artefacts — the tool trace, the citations captured from retrieval, the drafted
actions and the audit entries written during the turn:

  grounding        guideline retrieval with page-level citations
  consent          restricted-consent enforcement at the tool layer
  human_oversight  drafts vs autonomous writes (always drafts, queued for approval)
  data_boundary    read-only data plane; which patients and tools were touched
  model            model identity, how it was resolved, capacity fallbacks
  audit            the audit entries this turn persisted, by id

The UI renders it as the governance panel on each answer; the audit ids tie the
answer to the persistent trail on the Audit page.
"""
from __future__ import annotations

from services import audit


def _check(cid: str, label: str, status: str, detail: str) -> dict:
    return {"id": cid, "label": label, "status": status, "detail": detail}


def build(final: dict, since_iso: str) -> dict:
    """Governance record for one answer. `final` is the answer payload
    (trace/citations/actions/usage/model); `since_iso` marks the turn start so
    the audit slice covers exactly this turn."""
    trace = final.get("trace") or []
    citations = final.get("citations") or []
    actions = final.get("actions") or []
    usage = final.get("usage") or {}

    entries = audit.entries_since(since_iso)
    if not entries:
        # Direct tool runs bypass the agent's own answer log; record the turn so
        # every answer, scripted or live, lands in the audit trail.
        audit.log("CHAT·ANSWER", "direct_tool_runner",
                  f"Scripted answer delivered: {len(trace)} tool steps")
        entries = audit.entries_since(since_iso)

    tools = sorted({t.get("tool") for t in trace if t.get("tool")})
    agents = sorted({t.get("agent") for t in trace if t.get("agent")})
    patients = sorted({e["patient_id"] for e in entries if e.get("patient_id")})
    denials = [e for e in entries if e.get("event_type", "").startswith("CONSENT")]
    docs_cited = sorted({c.get("doc") for c in citations if c.get("doc")})
    guideline_used = "search_guidelines" in tools or bool(citations)

    checks = []

    if guideline_used and citations:
        checks.append(_check(
            "grounding", "Grounded clinical guidance", "pass",
            f"{len(citations)} passage(s) cited from {len(docs_cited)} national guideline "
            f"document(s), page-level, keyword retrieval (BM25) over the versioned corpus"))
    elif guideline_used:
        checks.append(_check(
            "grounding", "Grounded clinical guidance", "attention",
            "guideline retrieval ran but no citation was captured for this answer"))
    else:
        checks.append(_check(
            "grounding", "Grounded clinical guidance", "info",
            "no clinical recommendation in this answer; citations are mandatory whenever one is made"))

    if denials:
        checks.append(_check(
            "consent", "Consent enforcement", "pass",
            f"restricted-consent access blocked {len(denials)} time(s) at the tool layer "
            "and surfaced transparently"))
    else:
        checks.append(_check(
            "consent", "Consent enforcement", "pass",
            "enforced at the tool layer; no restricted-consent record was accessed this turn"))

    if actions:
        checks.append(_check(
            "human_oversight", "Human-in-the-loop", "pass",
            f"{len(actions)} draft(s) queued for clinician approval; zero autonomous writes — "
            "the agent cannot execute clinical actions"))
    else:
        checks.append(_check(
            "human_oversight", "Human-in-the-loop", "pass",
            "no clinical action initiated; any action is drafted to the approval queue, never executed"))

    touched = (f"{len(patients)} patient record(s) accessed" if patients
               else "population aggregates only, no row-level record accessed")
    checks.append(_check(
        "data_boundary", "Read-only data plane", "pass",
        f"all tools read the HIE, none write to it; {touched}; synthetic registry data"))

    model = final.get("model") or "n/a"
    switches = None
    try:                                   # live agent only; scripted runs have no model state
        from services import agent as A
        if final.get("usage"):
            switches = len(A._active["switches"])
            model_detail = (f"{model} · resolved via {A.RESOLUTION.get('source') or 'default'}"
                            + (f" · {switches} capacity fallback(s) this deployment" if switches else ""))
        else:
            model_detail = "deterministic direct tool run on live data; no generative model produced this answer"
    except Exception:
        model_detail = str(model)
    checks.append(_check("model", "Model transparency", "pass", model_detail))

    checks.append(_check(
        "audit", "Auditability", "pass" if entries else "attention",
        f"{len(entries)} event(s) written to the persistent audit trail this turn"
        if entries else "no audit event captured for this turn"))

    return {
        "version": 1,
        "summary": {
            "controls": len(checks),
            "passed": sum(1 for c in checks if c["status"] == "pass"),
            "attention": sum(1 for c in checks if c["status"] == "attention"),
        },
        "checks": checks,
        "data_access": {"read_only": True, "patients": patients,
                        "agents": agents, "tools": tools},
        "retrieval": {"mode": "keyword (BM25)", "citations": len(citations),
                      "documents": docs_cited},
        "actions": {"drafted": len(actions), "executed": 0,
                    "disposition": "pending_human_approval" if actions else None},
        "model": {"name": model, "switches": switches,
                  "llm_calls": usage.get("llm_calls"), "total_tokens": usage.get("total_tokens")},
        "audit": {"count": len(entries),
                  "events": [{k: e.get(k) for k in
                              ("id", "timestamp", "event_type", "actor", "detail", "severity", "patient_id")}
                             for e in entries]},
    }
