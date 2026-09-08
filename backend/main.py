"""
Nabd (نبض) — National Population Health Intelligence.

FastAPI backend: multi-agent chat (Google ADK + Gemini), dashboards, HITL queue,
audit trail, guideline documents, HIE data browser. Serves the built React
frontend from frontend/dist in production (single container, Railway-ready).
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routers import chat, dashboards, evals, ops
from services import agent, audit, hie, rag

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


# Warm-up state — the agent graph and model resolution happen in the background so the
# process answers /api/health within seconds of boot (Railway's healthcheck must not wait on
# the Gemini API). Chat requests that arrive before warm-up completes simply build the runner.
WARM = {"ready": False, "error": None, "seconds": None, "self_test": None}


def _warm_up():
    t0 = time.time()
    try:
        model = agent.resolve_model()
        print(f"· Model resolution: {model} — {agent.RESOLUTION['source']}"
              + (f" · error: {agent.RESOLUTION['error']}" if agent.RESOLUTION.get("error") else "")
              + (f" · visible: {', '.join(agent.RESOLUTION['visible'][:8])}" if agent.RESOLUTION.get("visible") else ""),
              flush=True)
        agent._get_runner()
        test = agent.self_test()
        WARM["self_test"] = test
        WARM["seconds"] = round(time.time() - t0, 1)
        WARM["ready"] = True
        if test.get("ok"):
            print(f"✓ Multi-agent mode ready in {WARM['seconds']}s: Gemini · model {model} answered in "
                  f"{test['ms']} ms (ADK supervisor + 5 specialists + MCP)", flush=True)
        else:
            print(f"✗ Gemini self-test FAILED for {model}: {test.get('error') or test} — "
                  f"free-form chat will fall back to the scripted engine until this is fixed", flush=True)
    except Exception as e:                      # never take the process down over warm-up
        WARM["error"] = f"{type(e).__name__}: {e}"
        print(f"✗ Agent warm-up failed (chat will retry on first request): {WARM['error']}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    t0 = time.time()
    t = hie.tables()
    print(f"✓ HIE loaded: {len(t['patient_summary']):,} patients, "
          f"{len(t['observations']):,} observations, {len(t['encounters']):,} encounters "
          f"({time.time() - t0:.1f}s)", flush=True)
    rag.ensure_loaded()
    print(f"✓ Guideline corpus: {rag.status()}", flush=True)
    if agent.llm_enabled():
        print("✓ GEMINI_API_KEY present — warming the agent graph in the background", flush=True)
        threading.Thread(target=_warm_up, name="nabd-warmup", daemon=True).start()
    else:
        print("✓ Scripted mode: no GEMINI_API_KEY — scenario chips run on live data; free-form chat disabled", flush=True)
    audit.log("SYSTEM·START", "nabd",
              f"Backend started — mode={'multi-agent' if agent.llm_enabled() else 'scripted'}")
    print(f"✓ Startup complete in {time.time() - t0:.1f}s · listening on port {os.getenv('PORT', '8000')}", flush=True)
    yield


app = FastAPI(title="Nabd — Population Health Intelligence", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

app.include_router(chat.router)
app.include_router(dashboards.router)
app.include_router(ops.router)
app.include_router(evals.router)


@app.get("/api/health")
def health():
    live = agent.llm_enabled()
    return {"status": "ok", "app": "nabd",
            "mode": "multi-agent" if live else "scripted",
            "model": (agent.resolve_model() if WARM["ready"] else "warming") if live else None,
            "model_source": agent.RESOLUTION.get("source") if live else None,
            "warmup": WARM if live else None,
            "patients": len(hie.summary())}


# ── Serve the built frontend (production) ──
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        candidate = FRONTEND_DIST / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
