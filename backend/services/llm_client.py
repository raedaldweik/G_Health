"""One place that knows how to talk to the language models.

  provider()            anthropic | gemini | none, the model behind the agent graph
  make_anthropic_client Anthropic SDK client (async by default) for the agent and the simulator
  make_client           google-genai client, used when Gemini is the provider
  gemini_available()    whether a Gemini credential exists at all
"""
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


def provider() -> str:
    return P.llm_provider()


def llm_available() -> bool:
    return provider() != "none"


def gemini_available() -> bool:
    """A Gemini credential of any kind."""
    return P.VERTEX or bool(P.API_KEY)


def describe() -> str:
    p = provider()
    if p == "anthropic":
        return "Anthropic API · API key"
    if P.VERTEX:
        return f"Vertex AI · project {P.PROJECT or '?'} · location {P.VERTEX_LOCATION} · service-account auth"
    if P.API_KEY:
        return "Gemini API · API key"
    return "no LLM credentials"


def make_anthropic_client(async_client: bool = True, timeout_s: float = 45.0, max_retries: int = 3):
    """Anthropic SDK client with a hard per-request timeout and the SDK's own backoff on
    429 / 5xx / connection errors. The key is injected explicitly so a stray
    ANTHROPIC_BASE_URL or profile on the host cannot redirect the demo."""
    import anthropic
    if not P.ANTHROPIC_KEY:
        raise RuntimeError("No Anthropic credentials: set ANTHROPIC_API_KEY")
    cls = anthropic.AsyncAnthropic if async_client else anthropic.Anthropic
    return cls(api_key=P.ANTHROPIC_KEY, timeout=timeout_s, max_retries=max_retries)


def make_client(http_options=None):
    """google-genai client for the Gemini provider (raises if no credential)."""
    from google import genai
    if P.VERTEX:
        return genai.Client(vertexai=True, project=P.PROJECT or None, location=P.VERTEX_LOCATION,
                            http_options=http_options)
    if P.API_KEY:
        return genai.Client(api_key=P.API_KEY, http_options=http_options)
    raise RuntimeError("No Gemini credentials: set GEMINI_API_KEY, or GOOGLE_GENAI_USE_VERTEXAI=TRUE with GOOGLE_CLOUD_PROJECT")
