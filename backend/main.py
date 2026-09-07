"""
Nabd (نبض) — National Population Health Intelligence.

FastAPI backend: multi-agent chat (Google ADK + Gemini), dashboards, HITL queue,
audit trail, guideline documents, HIE data browser. Serves the built React
frontend from frontend/dist in production (single container, Railway-ready).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routers import chat, dashboards, evals, ops
from services import agent, audit, hie, rag

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = hie.tables()
    print(f"✓ HIE loaded: {len(t['patient_summary']):,} patients, "
          f"{len(t['observations']):,} observations, {len(t['encounters']):,} encounters")
    rag.ensure_loaded()
    print(f"✓ Guideline corpus: {rag.status()}")
    if agent.llm_enabled():
        print(f"✓ Multi-agent mode: Gemini · model {agent.resolve_model()} (ADK supervisor + 5 specialists + MCP)")
        agent._get_runner()          # warm the agent graph so the first question isn't slow
    else:
        print("✓ Scripted mode: no GEMINI_API_KEY — scenario chips run on live data; free-form chat disabled")
    audit.log("SYSTEM·START", "nabd",
              f"Backend started — mode={'multi-agent' if agent.llm_enabled() else 'scripted'}")
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
    return {"status": "ok", "app": "nabd",
            "mode": "multi-agent" if agent.llm_enabled() else "scripted",
            "model": agent.resolve_model() if agent.llm_enabled() else None,
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
