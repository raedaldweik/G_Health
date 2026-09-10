# population-health-mcp ★

**The first population-health MCP server on Google Cloud's healthcare stack.**

## The gap (verified 2026-09-07)

| What Google ships | What it does | What it can't do |
|---|---|---|
| MCP Toolbox `cloud-healthcare` source (official, Nov 2025) | 15 read-only tools: FHIR store metadata, `get_fhir_resource`, `fhir_patient_search`, `fhir_patient_everything`, DICOM search | Single-patient lookups only |
| Agent Platform remote MCP server (official, June 2026) | `/mcp/predict` (endpoint scoring), `/mcp/models` (registry), `/mcp/evaluation`, … | Generic ML plumbing, no clinical semantics |
| 50+ Google-managed MCP servers (Next '26) | BigQuery `execute_sql`, Cloud Run, GKE, Workspace… | No healthcare population reasoning |
| Community FHIR MCP servers (wso2, the-momentum, …) | FHIR CRUD wrappers | Record plumbing, not population intelligence |

**Nothing lets an agent reason about a population**: quality measures, care gaps,
cohort building, model-backed risk stratification, counterfactual policy
simulation, or a *safe* write-back path. This server does exactly that — checked
against GitHub (google/googleapis/GoogleCloudPlatform orgs), PulseMCP (22k+
servers), mcpservers.org and mcpmarket.

## Tools

| Tool | What it answers |
|---|---|
| `get_population_snapshot` | "How is the nation doing?" — registry KPIs |
| `build_cohort` | "Uncontrolled T2DM over 65 in Al Rayyan" — declarative criteria |
| `find_care_gaps` | "Who has an open statin gap, by facility?" |
| `compute_quality_measure` | HEDIS-style measures with numerator/denominator vs target |
| `stratify_risk` | Score any cohort through the deployed XGBoost risk model |
| `simulate_policy` | Counterfactual what-if: flip the therapy, re-score the cohort |
| `draft_intervention` | DRAFT-ONLY interventions → human approval queue (never writes to the EMR) |

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

**Claude Desktop** (`claude_desktop_config.json`) — identical block under
`mcpServers`.

**Inside Nabd**: the ADK supervisor's `pophealth_agent` connects via
`McpToolset(StdioConnectionParams(...))` — the hop is visible in the UI agent trace.

## On Google Cloud

Same seven tools, re-hosted as a remote MCP server on Cloud Run: cohorts and
measures become BigQuery SQL over the streamed FHIR export, `stratify_risk` calls a
Vertex AI online endpoint, and `draft_intervention` writes draft FHIR `Task`
resources to the Cloud Healthcare API store — sitting beside Google's official
servers, filling the layer they don't cover.
