"""
Where Nabd is running and which backends are live.

Railway / local:   tables from csv.gz; the language model through an API key.
Google Cloud:      HIE_BACKEND=bigquery, the model via Vertex AI with the Cloud Run
                   service account, region me-central1 (Doha).

Language-model provider (LLM_PROVIDER, default auto):
  anthropic  ANTHROPIC_API_KEY, claude-sonnet-4-6 by default (the demo backend)
  gemini     GEMINI_API_KEY / GOOGLE_API_KEY, or Vertex AI with a service account
Auto picks anthropic when its key is present, else gemini, else no LLM (direct tool mode).
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
ANTHROPIC_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "auto").strip().lower()      # auto | anthropic | gemini | none

COMPUTE = ("cloud-run" if os.getenv("K_SERVICE")
           else "railway" if os.getenv("RAILWAY_ENVIRONMENT_NAME") or os.getenv("RAILWAY_PROJECT_ID")
           else "local")
REGION = os.getenv("NABD_REGION", "").strip() or ("me-central1" if COMPUTE == "cloud-run" else None)
SERVICE = os.getenv("K_SERVICE") or os.getenv("RAILWAY_SERVICE_NAME") or "nabd"
REVISION = os.getenv("K_REVISION") or os.getenv("RAILWAY_GIT_COMMIT_SHA", "")[:7] or None


def llm_provider() -> str:
    """anthropic | gemini | none, honouring an explicit LLM_PROVIDER when its credentials exist."""
    gemini_ok = VERTEX or bool(API_KEY)
    if LLM_PROVIDER == "none":
        return "none"
    if LLM_PROVIDER == "anthropic":
        return "anthropic" if ANTHROPIC_KEY else "none"
    if LLM_PROVIDER == "gemini":
        return "gemini" if gemini_ok else "none"
    if ANTHROPIC_KEY:
        return "anthropic"
    return "gemini" if gemini_ok else "none"


def llm_backend() -> str:
    p = llm_provider()
    if p == "anthropic":
        return "anthropic-api"
    if p == "gemini":
        return "vertex" if VERTEX else "gemini-api"
    return "none"


def info() -> dict:
    from services import bq
    return {
        "compute": COMPUTE, "region": REGION, "service": SERVICE, "revision": REVISION,
        "project": PROJECT or None,
        "data": bq.STATUS,
        "llm": llm_backend(), "vertex_location": VERTEX_LOCATION if VERTEX else None,
        "cloud_native": bool(COMPUTE == "cloud-run" or HIE_BACKEND == "bigquery" or VERTEX),
    }
