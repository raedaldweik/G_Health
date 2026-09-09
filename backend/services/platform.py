"""
Where Nabd is running and which backends are live.

Phase 1 (Railway / local): tables from csv.gz, Gemini via an API key.
Phase 2 (Google Cloud):    HIE_BACKEND=bigquery, Gemini + embeddings via Vertex AI with the
                           Cloud Run service account, region me-central1 (Doha).
Everything here is read from the environment once; /api/health reports it so the UI can
say truthfully what it is running on.
"""
from __future__ import annotations

import os

PROJECT = (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("BQ_PROJECT") or "").strip()
BQ_DATASET = os.getenv("BQ_DATASET", "nabd_hie").strip()
BQ_LOCATION = os.getenv("BQ_LOCATION", "me-central1").strip()
HIE_BACKEND = os.getenv("HIE_BACKEND", "local").strip().lower()          # local | bigquery
BQ_AUTOLOAD = os.getenv("BQ_AUTOLOAD", "1").lower() in ("1", "true", "yes")

VERTEX = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().upper() in ("TRUE", "1", "YES")
VERTEX_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "global").strip() or "global"
API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

COMPUTE = ("cloud-run" if os.getenv("K_SERVICE")
           else "railway" if os.getenv("RAILWAY_ENVIRONMENT_NAME") or os.getenv("RAILWAY_PROJECT_ID")
           else "local")
REGION = os.getenv("NABD_REGION", "").strip() or ("me-central1" if COMPUTE == "cloud-run" else None)
SERVICE = os.getenv("K_SERVICE") or os.getenv("RAILWAY_SERVICE_NAME") or "nabd"
REVISION = os.getenv("K_REVISION") or os.getenv("RAILWAY_GIT_COMMIT_SHA", "")[:7] or None


def llm_backend() -> str:
    if VERTEX:
        return "vertex"
    if API_KEY:
        return "gemini-api"
    return "none"


def info() -> dict:
    from services import bq
    return {
        "compute": COMPUTE, "region": REGION, "service": SERVICE, "revision": REVISION,
        "project": PROJECT or None,
        "data": bq.STATUS,
        "llm": llm_backend(), "vertex_location": VERTEX_LOCATION if VERTEX else None,
        "phase": 2 if (COMPUTE == "cloud-run" or HIE_BACKEND == "bigquery" or VERTEX) else 1,
    }
