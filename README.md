# Nabd (نبض) — National Population Health Intelligence

An agentic AI platform on top of a national Health Information Exchange, built with
**Google's agentic stack**: Gemini + the Agent Development Kit (ADK) multi-agent
orchestration, grounded RAG with citations, four real ML models, a counterfactual
policy simulator, human-in-the-loop safety — and the ★ **first population-health MCP
server on Google Cloud's healthcare stack**.

All patient data is synthetic (4,000-patient cardiometabolic registry, 36 months of
longitudinal coded records). Built as a Google Cloud AI Customer Engineer demo;
Phase 2 moves the same contracts onto Cloud Healthcare API FHIR (me-central1, Doha),
BigQuery (ML + AI.FORECAST/TimesFM + VECTOR_SEARCH) and Agent Engine.

---

## What's inside

| Layer | Phase 1 (this repo, Railway-deployable) | Phase 2 (Google Cloud native) |
|---|---|---|
| Data | 8-table relational HIE (patients, conditions, observations, medications, encounters, care gaps) + FHIR R4 sample bundle | Cloud Healthcare API FHIR R4 store → BigQuery streaming export (ANALYTICS_V2) |
| ML | XGBoost complication risk (**AUC 0.853** vs 0.774 legacy score, SHAP explanations) · KMeans segments · patient similarity · seasonal demand forecast | BigQuery ML BOOSTED_TREE → Vertex Model Registry → online endpoint · AI.FORECAST (TimesFM) · VECTOR_SEARCH |
| Agents | **ADK supervisor + 5 specialists** (cohort, guidelines, risk/ML, pop-health MCP, actions) on Gemini 3.8 Flash | Same graph on Cloud Run in me-central1 (sessions in AlloyDB, OTel → Cloud Trace); Agent Engine when offered in Doha |
| RAG | Hybrid BM25 + gemini-embedding-001 over national guideline PDFs, page-level citations | Vertex AI RAG Engine managed corpus |
| MCP | ★ `pophealth_mcp` — quality measures, care gaps, cohorts, model-backed stratification, counterfactual simulation, draft-only write-back | Same server re-hosted on Cloud Run beside Google's official BigQuery + cloud-healthcare MCP tools |
| Simulation | Counterfactual re-scoring of the eligible cohort through the risk model (never canned numbers) | Identical logic as ML.PREDICT over counterfactual rows |
| Safety | Consent enforcement, HITL approval queue, full audit trail | FHIR consent enforcement, Cloud Audit Logs |
| Evaluation | **AI Evaluation tab** — held-out ROC/PR/calibration/threshold economics/subgroup fairness for the risk model; golden agent evalset (trajectory recall, groundedness, action safety, numeric faithfulness, latency, cost); LLM selection matrix with measured flat-vs-hierarchical token cost; governance checklist | `adk eval` in Cloud Build as a release gate + Gen AI Evaluation Service judge + weekly production sampling |
| Architecture | **Architecture tab** — interactive 6-lane target design with animated flows, click-through node rationale, real-time vs batch table, scale & inference model, 10 ADRs, phase map, Doha list-price run cost | The Terraform for it |
| UI | React glass UI: assistant with live agent trace, 5 storytelling dashboards (incl. facility map), architecture, evaluation, queue, documents, HIE browser, audit | + Looker embeds |

## Quickstart

```bash
# 1) Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.train_models          # trains the 4 models from the committed HIE data (~30s)
cp .env.example .env                    # optional: add GEMINI_API_KEY for the live multi-agent mode
uvicorn main:app --reload --port 8000

# 2) Frontend (second terminal)
cd frontend
npm install
npm run dev                             # http://localhost:5173 (proxies /api → :8000)
```

**No API key?** Everything still works: the scenario chips run a scripted engine that
calls the same live services (HIE queries, RAG, model scoring, the simulator, the
queue) — only free-form chat requires `GEMINI_API_KEY`
([aistudio.google.com/apikey](https://aistudio.google.com/apikey)). This doubles as
the demo-day failover: if the live agent errors mid-scenario, the backend
automatically falls back to the scripted engine.

Regenerate the synthetic HIE from scratch (deterministic, seeded):
`python -m scripts.generate_hie_data`.

## Deploy to Railway

Push to GitHub → Railway → **New Project → Deploy from GitHub repo**. The
`Dockerfile` builds the frontend, installs the backend, **trains the models at image
build time**, and serves everything on one `$PORT`. Set `GEMINI_API_KEY` in the
service Variables tab. Health check: `/api/health`.

## The population-health MCP server ★

Google ships MCP tools to **read** FHIR (MCP Toolbox `cloud-healthcare`) and to
**call** ML plumbing (Agent Platform `/mcp/predict`). Nothing — official or
community — lets an agent reason about a **population**. `backend/pophealth_mcp`
fills that gap with 7 tools (measures, gaps, cohorts, stratification, simulation,
draft-only interventions) and speaks stdio to **any** MCP client:

```bash
cd backend && python -m pophealth_mcp        # or plug into Gemini CLI / Claude Desktop
```

See [backend/pophealth_mcp/README.md](backend/pophealth_mcp/README.md) for client
configs and the full gap analysis. Inside Nabd, the ADK supervisor connects to it
through `McpToolset` — a genuine MCP hop you can watch in the UI's agent trace.

## Repo layout

```
backend/
  main.py                FastAPI app (serves API + built frontend)
  routers/               chat (NDJSON streaming) · dashboards · evals · queue/audit/docs/data
  services/
    hie.py               the HIE query engine (single source of truth for chat + dashboards)
    ml.py                model scoring, SHAP drivers, similarity, segments, counterfactual simulator
    rag.py               hybrid retrieval over guideline PDFs (BM25 + gemini-embedding cache)
    agent.py             ADK multi-agent graph + NDJSON event streaming
    scenarios.py         scripted demo engine (same services, real numbers, demo-day failover)
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
docs/STORYLINE.md        the full interview storyline, run-of-show and Q&A prep
```

## Disclaimer

All patient records are synthetic; clinical scenarios are illustrative. The real
MOPH guideline PDFs are included solely as a retrieval corpus for demonstration.
Not for clinical use.
