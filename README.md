# Nabd (نبض): National Population Health Intelligence

An agentic AI assistant on top of a national Health Information Exchange, built with Google's
agentic stack: the Agent Development Kit (a supervisor and five specialists on a function-calling model), grounded
retrieval with page-level citations over the national clinical guidelines, four trained ML models
with model cards and held-out evaluation, a patient risk sensitivity simulator, predictive population risk
scenarios, a human-in-the-loop approval queue, a full audit trail, and a population-health MCP
server that any MCP client can use.

All patient data is synthetic: a 4,000-patient national diabetes registry with 36 months of
longitudinal, coded records and a FHIR R4 export sample. Built as a Google Cloud AI Customer
Engineer demonstration. The deck (`deck/Nabd.pptx`) carries the Google Cloud
reference architecture; the app runs on one container today and maps component by component to
managed services in me-central1 (Doha).

---

## What's inside

| Layer | In this build | On Google Cloud |
|---|---|---|
| Data | 8-table relational HIE (patients, encounters, conditions, medications, observations, care gaps, facilities, patient summary) plus a FHIR R4 sample bundle | Cloud Healthcare API FHIR store, streaming export to BigQuery, Dataform marts |
| ML | XGBoost deterioration model with monotonic clinical constraints (held-out AUC 0.854 vs 0.809 for the registry's rule-based score), SHAP-style drivers; KMeans segments; patient similarity; seasonal demand forecast | BigQuery ML BOOSTED_TREE_CLASSIFIER, Vertex AI Model Registry and online endpoint, BigQuery AI.FORECAST (TimesFM), VECTOR_SEARCH |
| Agents | ADK supervisor plus five specialists (data, guidelines, risk, population-health MCP, actions) on a hosted function-calling model (provider-agnostic: Anthropic API by default, Gemini optional), with a tested fallback chain and a direct tool runner that runs the same tools without the language model | Same graph on Cloud Run in me-central1 with sessions in AlloyDB; Agent Engine when available in region |
| Retrieval | Hybrid BM25 plus gemini-embedding-001 over the national guideline PDFs, cached once, page-level citations | Vertex AI RAG Engine over a Cloud Storage corpus |
| MCP | `pophealth_mcp`: population snapshot, cohorts, care gaps, quality measures, stratification, predictive risk scenarios, draft-only interventions (review tasks, recalls, referrals; never a prescription) | Cloud Run service beside Google's MCP Toolbox for BigQuery and FHIR |
| Simulation | Patient risk sensitivity analysis with live re-scoring, attribution, rule-based gaps and a narrated explanation; predictive population risk scenarios (re-score a cohort with one input changed; never events prevented or savings) | ML.PREDICT over counterfactual rows |
| Safety | Consent enforcement at the tool layer, human approval queue, audit trail, numbers only from tools, citations on every clinical claim | FHIR consent enforcement, Model Armor, Cloud Audit Logs, Cloud Trace |
| Evaluation | Held-out ROC, precision-recall, calibration, threshold economics and subgroup fairness; golden agent evalset (trajectory, groundedness, action safety, numeric faithfulness); model choice with list prices; governance controls | Gen AI Evaluation Service as judge in Cloud Build |
| UI | React glass UI: assistant with live agent trace, cross-filtered dashboards (registry, clinical quality, deterioration risk, cost and population variation, geography), simulator, evaluation, queue, documents, HIE browser, audit; Arabic and English voice | Identity-Aware Proxy in front; Looker for published KPIs |

## Quickstart

```bash
# 1) Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.train_models          # trains the 4 models from the committed HIE data (~30s)
cp .env.example .env                    # add ANTHROPIC_API_KEY for the live multi-agent mode (GEMINI_API_KEY for embeddings)
uvicorn main:app --reload --port 8000

# 2) Frontend (second terminal)
cd frontend
npm install
npm run dev                             # http://localhost:5173 (proxies /api → :8000)
```

**No API key?** Everything still works: the scenario chips run the tools directly, a runner that
calls the same live services (HIE queries, RAG, model scoring, the simulator, the
queue). Only free-form chat and the simulator's narrated explanation need model credentials
(`ANTHROPIC_API_KEY`, or a Gemini credential with `LLM_PROVIDER=gemini`, from
[aistudio.google.com/apikey](https://aistudio.google.com/apikey)). This doubles as
the demo-day failover: if the live agent errors mid-scenario, the backend
automatically falls back to the direct tool runner.

Regenerate the synthetic HIE from scratch (deterministic, seeded):
`python -m scripts.generate_hie_data`.

## Guideline retrieval and the semantic index

Guideline PDFs are chunked once (cached in `backend/data/runtime/ragchunks-*.json`, committed).
The semantic index (`gemini-embedding-001`, 768 dimensions) is also computed once and cached as
`backend/data/runtime/ragembed-<corpus hash>-gemini-embedding-001.npz`. Build it locally with a
key that has embedding quota and commit the file, so deployments load it instead of embedding:

```bash
cd backend && GEMINI_API_KEY=... python -m scripts.embed_corpus
git add backend/data/runtime/ragembed-*.npz && git commit -m "Add the guideline semantic index"
```

Without the cache, retrieval is BM25 keyword search until the background build succeeds; the
Documents tab says which mode is active. The map basemap is OpenFreeMap (no API key). Set
`VITE_BASEMAP_STYLE` at build time to use a different MapLibre style.

## Deploy to Railway

Push to GitHub → Railway → **New Project → Deploy from GitHub repo**. The
`Dockerfile` builds the frontend, installs the backend, **trains the models at image
build time**, and serves everything on one `$PORT`. Set `ANTHROPIC_API_KEY` (and optionally `GEMINI_API_KEY` for the embeddings) in the
service Variables tab. Health check: `/api/health`.

## The population-health MCP server ★

Google already provides MCP connectivity to the core data services (MCP Toolbox sources for
BigQuery and the Cloud Healthcare API FHIR store). `backend/pophealth_mcp`
adds the population-health layer with 7 tools (measures, gaps, cohorts, stratification, predictive risk scenarios,
draft-only interventions) and speaks stdio to **any** MCP client:

```bash
cd backend && python -m pophealth_mcp        # or plug into Gemini CLI / Claude Desktop
```

See [backend/pophealth_mcp/README.md](backend/pophealth_mcp/README.md) for client
configs and the full gap analysis. Inside Nabd, the ADK supervisor connects to it
through `McpToolset`, a genuine MCP hop you can watch in the UI's agent trace.

## Repo layout

```
backend/
  main.py                FastAPI app (serves API + built frontend)
  routers/               chat (NDJSON streaming) · dashboards · evals · queue/audit/docs/data
  services/
    hie.py               the HIE query engine (single source of truth for chat + dashboards)
    ml.py                model scoring, SHAP drivers, similarity, segments, predictive risk scenarios
    rag.py               hybrid retrieval over guideline PDFs (BM25 + gemini-embedding cache)
    agent.py             ADK multi-agent graph + NDJSON event streaming
    scenarios.py         direct tool runner for the chips (same services, real numbers, demo-day failover)
    queue_service.py     human-in-the-loop approval queue
    audit.py             governance trail
    evals.py             evaluation harness: held-out model metrics, agent evalset runner, LLM cost model, governance
    geo.py               facility geography (map payloads, regional roll-ups)
  pophealth_mcp/         ★ the population-health MCP server (FastMCP, stdio)
  scripts/
    generate_hie_data.py deterministic synthetic HIE generator (+ FHIR R4 export)
    train_models.py      trains the 4 models, writes model_cards.json + held-out predictions for the eval tab
  data/hie/              the committed synthetic exchange (8 tables, csv.gz)
  data/guidelines/       national clinical guideline PDFs (RAG corpus)
  data/fhir_sample/      FHIR R4 NDJSON sample bundle (Patient/Condition/Observation/…)
  data/evals/            golden agent evalset (10 cases, ADK-compatible shape)
frontend/                React + Vite + Tailwind + Recharts + MapLibre glass UI
  src/data/architecture.js   the target-architecture content (nodes, flows, ADRs, phases, cost model)
  src/pages/ArchitecturePage.jsx · EvaluationPage.jsx
docs/DEMO_SCRIPT.md (run of show) and docs/BRIEF.md (the complete brief)
```

## Disclaimer

All patient records are synthetic; clinical scenarios are illustrative. The real
MOPH guideline PDFs are included solely as a retrieval corpus for demonstration.
Not for clinical use.
