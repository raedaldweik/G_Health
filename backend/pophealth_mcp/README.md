# population-health-mcp

**Domain-specific population-health operations, exposed as MCP tools beside Google's own data connectivity.**

## Where it sits

Google already provides MCP connectivity to the core data services this system relies on:
the MCP Toolbox has an official `cloud-healthcare` source (FHIR store metadata, resource
reads, patient search, `$everything`) and a `bigquery` source (SQL over the warehouse).
Those tools answer record-level and table-level questions.

Nabd's server adds the population-health layer on top of that data: quality measures,
cohort construction, care-gap identification, model-backed stratification, predictive
risk scenarios, and a human-approved drafting path for interventions. It is a small,
domain-specific service, not a replacement for the platform's tools.

## Tools

| Tool | What it answers |
|---|---|
| `get_population_snapshot` | "How is the registry doing?" — headline KPIs |
| `build_cohort` | "Uncontrolled type 2 over 65 in Al Rayyan" — declarative criteria |
| `find_care_gaps` | "Who has an open retinal-screening gap, by facility?" |
| `compute_quality_measure` | HEDIS-style measures with numerator/denominator vs target |
| `stratify_risk` | Score any cohort through the deployed XGBoost risk model |
| `risk_scenario` | Predictive scenario: re-score a cohort with one input changed and report the shift in predicted risk. Predictive, not causal; never events prevented or savings |
| `draft_intervention` | DRAFT-ONLY review lists, recalls, referrals, outreach → human approval queue (never writes to the EMR; never a prescription) |

## Use it from any MCP client

Runs over stdio. From `backend/` (with its requirements installed):

```bash
python -m pophealth_mcp
```

**Gemini CLI** (`~/.gemini/settings.json`):

```json
{
  "mcpServers": {
    "population-health": {
      "command": "python",
      "args": ["-m", "pophealth_mcp"],
      "cwd": "/absolute/path/to/g_health/backend"
    }
  }
}
```

**Claude Desktop** (`claude_desktop_config.json`): identical block under `mcpServers`.

**Inside Nabd**: the ADK supervisor's `pophealth_agent` connects via
`McpToolset(StdioConnectionParams(...))`; the hop is visible in the UI agent trace.

## On Google Cloud (target architecture, to validate in discovery)

The same seven tools re-hosted as a remote MCP server on Cloud Run in `me-central1`:
cohorts and measures become BigQuery SQL over the FHIR export, `stratify_risk` calls a
Vertex AI online endpoint, and `draft_intervention` writes draft FHIR `Task` resources
to the Cloud Healthcare API store for a clinician to approve, beside the platform's own
MCP tools.
