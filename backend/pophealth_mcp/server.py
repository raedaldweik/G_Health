"""
population-health-mcp: domain-specific population-health operations as MCP tools.

Google already provides MCP connectivity to the core data services (the MCP Toolbox
sources for BigQuery and the Cloud Healthcare API FHIR store). This server adds the
population-health layer on top of that data: quality measures, cohort construction,
care-gap identification, model-backed stratification, predictive risk scenarios, and a
human-approved drafting path for interventions.

Tools:
  get_population_snapshot   headline KPIs for the whole registry
  build_cohort              declarative cohort from clinical criteria
  find_care_gaps            open guideline-derived gaps, filterable by gap/facility
  compute_quality_measure   HEDIS-style measures (numerator/denominator/rate/target)
  stratify_risk             score a cohort through the deployed risk model
  risk_scenario             predictive-risk scenario: re-score a cohort with changed inputs
  draft_intervention        DRAFT-ONLY intervention (review, recall, referral) → approval queue

Runs over stdio for any MCP client, the Nabd agent (ADK McpToolset), Gemini CLI,
Claude Desktop. Start from backend/:  python -m pophealth_mcp
On Google Cloud: the same tools re-hosted on Cloud Run beside the platform's own MCP
tools, backed by BigQuery and a Vertex AI endpoint instead of the local engine.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as a standalone MCP server from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from services import hie, ml
from services import queue_service

mcp = FastMCP(
    "population-health-mcp",
    instructions=(
        "Population-health reasoning over a national HIE cardiometabolic registry "
        "(4,000 synthetic patients). Use build_cohort/find_care_gaps/compute_quality_measure "
        "for population questions, stratify_risk and risk_scenario for the ML-backed "
        "prioritisation and predictive scenarios (predictive, not causal: never events "
        "prevented or savings), and draft_intervention to queue actions for human "
        "approval (nothing is ever written to the EMR autonomously)."),
)


def _j(obj) -> str:
    return json.dumps(obj, default=str)


@mcp.tool()
def get_population_snapshot() -> str:
    """Headline KPIs for the whole registry: cohort size, mean HbA1c, control rates,
    CVD prevalence, open care gaps, utilisation and total annual cost (QAR)."""
    return _j(hie.cohort_stats())


@mcp.tool()
def build_cohort(filters_json: str, select_columns_json: str = "", limit: int = 15) -> str:
    """Build a patient cohort from declarative clinical criteria.

    Args:
        filters_json: JSON list of {column, op, value} over the patient_summary table,
            e.g. '[{"column":"hba1c_latest","op":">","value":9},{"column":"age","op":">=","value":65}]'.
            Ops: ==, !=, >, <, >=, <=, between, contains, not_contains, in, not_in, is_null, not_null.
        select_columns_json: optional JSON list of columns to return per patient.
        limit: max patient rows to return (the matched count is always exact).
    """
    filters = json.loads(filters_json) if filters_json else []
    select = json.loads(select_columns_json) if select_columns_json else None
    return _j(hie.filter_cohort(filters, select_columns=select, limit=limit))


@mcp.tool()
def find_care_gaps(gap_key: str = "", facility: str = "", limit: int = 12) -> str:
    """Find open, guideline-derived care gaps across the population.

    Args:
        gap_key: optional filter, one of hba1c_overdue, retinal_screening_overdue,
            foot_exam_overdue, acr_screening_missing, bp_uncontrolled, glp1_sglt2_gap,
            therapy_inertia, low_adherence, renal_protection_gap. Empty = summary of all.
        facility: optional facility name filter (substring match).
        limit: max example patients to list for a specific gap.
    """
    if not gap_key:
        return _j({"gap_summary": hie.care_gap_summary()})
    s = hie.summary()
    sub = s[s["open_care_gaps"].str.contains(gap_key, na=False)]
    if facility:
        sub = sub[sub["facility_name"].str.contains(facility, case=False, na=False)]
    cols = ["patient_id", "full_name", "age", "facility_name", "registry_risk_tier",
            "hba1c_latest", "care_gap_count"]
    return _j({"gap_key": gap_key, "gap_label": hie.GAP_LABELS.get(gap_key, gap_key),
               "patients_with_gap": int(len(sub)),
               "by_facility": sub.groupby("facility_name").size().sort_values(ascending=False)
                                 .head(8).to_dict(),
               "example_patients": sub.sort_values("care_gap_count", ascending=False)
                                      .head(limit)[cols].to_dict("records")})


@mcp.tool()
def compute_quality_measure(measure_id: str = "") -> str:
    """Compute HEDIS-style clinical quality measures live from the HIE.

    Args:
        measure_id: one of NABD-DM-01 (HbA1c testing), NABD-DM-02 (HbA1c <8%),
            NABD-DM-03 (HbA1c >9%, lower is better), NABD-DM-04 (retinal screening),
            NABD-DM-05 (foot exam), NABD-DM-06 (ACR screening), NABD-DM-07 (BP control),
            NABD-DM-08 (SGLT2i/GLP-1 in eligible T2DM), NABD-DM-09 (RAAS in CKD/albuminuria),
            NABD-DM-10 (adherence ≥80%).
            Empty = the full measure set with met/not-met vs targets.
    """
    measures = hie.quality_measures()
    if measure_id:
        hit = [m for m in measures if m["measure_id"] == measure_id]
        return _j(hit[0] if hit else {"error": f"unknown measure '{measure_id}'",
                                      "available": [m["measure_id"] for m in measures]})
    return _j({"measures": measures})


@mcp.tool()
def stratify_risk(filters_json: str = "", top_n: int = 10) -> str:
    """Score a cohort through the deployed complication-risk ML model (XGBoost).
    Returns the model risk-band distribution, expected 12-month events, and the
    highest-risk patients for prioritisation.

    Args:
        filters_json: optional JSON cohort criteria as in build_cohort. Empty = whole registry.
        top_n: how many highest-risk patients to list.
    """
    filters = json.loads(filters_json) if filters_json else None
    return _j(ml.stratify_cohort(filters, top_n=top_n))


@mcp.tool()
def risk_scenario(scenario: str) -> str:
    """Population PREDICTIVE-RISK scenario: re-scores every eligible patient through the
    deployed deterioration-risk model with a hypothetical change to the model's inputs and
    reports the shift in the predicted-risk distribution (mean, bands, patients moving
    between bands, features accounting for the change). Predictive, not causal: the shift
    is never an estimate of events prevented, savings or return.

    Args:
        scenario: intensification_cohort_hba1c | hba1c_recall | adherence_support | bp_control.
    """
    return _j(ml.risk_scenario(scenario))


@mcp.tool()
def draft_intervention(patient_ids_json: str, action_type: str, title: str, rationale: str,
                       citation: str = "") -> str:
    """DRAFT a population intervention (recall campaign, clinical review list, referral
    batch, outreach task) for the listed patients. The draft is queued for HUMAN clinician
    approval; this tool never writes to the EMR and never drafts a prescription, drug or
    dose.

    Args:
        patient_ids_json: JSON list of patient ids, e.g. '["QH-100042","QH-100077"]'.
        action_type: recall_campaign | clinical_review | referral | outreach_task.
        title: short action title shown in the approval queue.
        rationale: clinical rationale (include the guideline basis).
        citation: optional guideline citation string.
    """
    pids = json.loads(patient_ids_json)
    item = queue_service.add_draft(
        action_type=action_type, title=title, detail=rationale,
        patient_id=pids[0] if len(pids) == 1 else "",
        patient_ids=pids, citation=citation, drafted_by="population-health-mcp")
    from services import audit
    audit.log("MCP·DRAFT", "population-health-mcp",
              f"Drafted {action_type} '{title}' for {len(pids)} patient(s) → approval queue",
              severity="action")
    return _j({"ok": True, "draft_id": item["id"], "status": "pending_human_approval",
               "patients": len(pids)})


def main():
    mcp.run()


if __name__ == "__main__":
    main()
