"""One place that knows how to talk to Gemini: Vertex AI (service account, phase 2) or the
Gemini API (key, phase 1). Every genai.Client in the codebase comes from here."""
from __future__ import annotations

import os

from services import platform as P

# ADK and google-genai read GOOGLE_API_KEY; accept the Gemini name too.
if P.API_KEY and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = P.API_KEY
if P.VERTEX:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    if P.PROJECT:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", P.PROJECT)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", P.VERTEX_LOCATION)
else:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "FALSE")


def llm_available() -> bool:
    return P.VERTEX or bool(P.API_KEY)


def describe() -> str:
    if P.VERTEX:
        return f"Vertex AI · project {P.PROJECT or '?'} · location {P.VERTEX_LOCATION} · service-account auth"
    if P.API_KEY:
        return "Gemini API · API key"
    return "no LLM credentials"


def make_client(http_options=None):
    """google-genai client for the configured backend (raises if none is configured)."""
    from google import genai
    if P.VERTEX:
        return genai.Client(vertexai=True, project=P.PROJECT or None, location=P.VERTEX_LOCATION,
                            http_options=http_options)
    if P.API_KEY:
        return genai.Client(api_key=P.API_KEY, http_options=http_options)
    raise RuntimeError("No LLM credentials: set GEMINI_API_KEY, or GOOGLE_GENAI_USE_VERTEXAI=TRUE with GOOGLE_CLOUD_PROJECT")
