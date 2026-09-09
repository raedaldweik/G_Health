# Nabd on Google Cloud (phase 2)

Same container as Railway, deployed to **Cloud Run in me-central1 (Doha)**, data in
**BigQuery** (`<project>.nabd_hie`), Gemini and embeddings through **Vertex AI** with the
Cloud Run service account — no API keys anywhere.

## Deploy (Cloud Shell, ~8 minutes)

```bash
git clone -b claude/google-ai-customer-engineer-7v9awy https://github.com/raedaldweik/G_Health.git
cd G_Health
bash deploy/gcp/bootstrap.sh <PROJECT_ID>
```

What the script does: enables Run/Build/Artifact Registry/BigQuery/Vertex APIs, creates the
`nabd-run` service account with BigQuery data editor + job user, Vertex AI user and log
writer, and runs `gcloud run deploy --source .` (Cloud Build builds the Dockerfile).

## First boot

If the dataset is empty the app serves from the committed csv files and provisions
BigQuery in the background (8 tables, ~280k rows, about a minute). Subsequent boots read
the tables from BigQuery. `/api/health` → `platform.data.loaded_from` tells you which.

## Environment variables the container understands

| Variable | Phase 2 value | Meaning |
|---|---|---|
| `HIE_BACKEND` | `bigquery` | read the HIE from BigQuery (default `local`) |
| `GOOGLE_CLOUD_PROJECT` | project id | BigQuery + Vertex project |
| `BQ_DATASET` / `BQ_LOCATION` | `nabd_hie` / `me-central1` | dataset + location |
| `GOOGLE_GENAI_USE_VERTEXAI` | `TRUE` | Gemini via Vertex AI (service account) |
| `GOOGLE_CLOUD_LOCATION` | `global` | Gemini endpoint location |
| `NABD_REGION` | `me-central1` | shown in the header / health |
| `MODEL` | optional | pin a model (e.g. `gemini-3.5-flash`) |
| `THINKING_LEVEL` | `LOW` | Gemini 3 thinking level for tool routing |

## Redeploy after a code change

```bash
git pull && gcloud run deploy nabd --source . --region me-central1
```
