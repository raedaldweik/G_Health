"""Chat API, streams NDJSON events (live agent steps → final payload)."""
from __future__ import annotations

import json
import os

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import agent, scenarios

router = APIRouter()

FORCE_SCENARIOS = os.getenv("FORCE_SCENARIOS", "").lower() in ("1", "true", "yes")


class ChatRequest(BaseModel):
    message: str = ""
    session_id: str = "default"
    persona: str = "clinician"
    scenario_id: str | None = None


@router.get("/api/scenarios")
def get_scenarios(persona: str = "clinician"):
    return {"persona": persona, "scenarios": scenarios.list_scenarios(persona),
            "llm_enabled": agent.llm_enabled(),
            "model": agent.active_model() if agent.llm_enabled() else None}


def _ndjson(gen):
    async def stream():
        async for ev in gen:
            yield json.dumps(ev, default=str) + "\n"
    return StreamingResponse(stream(), media_type="application/x-ndjson")


NO_KEY_NOTICE = (
    "**Free-form questions need a Gemini API key.** The suggested scenario chips run fully "
    "against the live data without one. To enable the full multi-agent experience, set "
    "`GEMINI_API_KEY` in the backend environment and restart."
)


@router.post("/api/chat")
async def chat(req: ChatRequest):
    use_scripted = req.scenario_id and (not agent.llm_enabled() or FORCE_SCENARIOS)

    if use_scripted:
        runner = scenarios.get_runner(req.scenario_id)
        if runner:
            return _ndjson(runner(req.persona))

    if not agent.llm_enabled():
        async def notice():
            yield {"type": "final", "answer": NO_KEY_NOTICE, "trace": [], "charts": [],
                   "citations": [], "actions": [], "usage": None, "model": None}
        return _ndjson(notice())

    async def run_with_fallback():
        try:
            async for ev in agent.stream_chat(req.message, req.session_id, req.persona):
                yield ev
        except Exception as e:
            # Live agent failed mid-demo: fall back to the scripted runner when we
            # have one, else surface a clean error.
            fb = scenarios.get_runner(req.scenario_id) if req.scenario_id else None
            if fb:
                yield {"type": "step", "status": "done", "agent": "system", "tool": "fallback",
                       "detail": f"live agent unavailable ({e.__class__.__name__}), scripted engine engaged"}
                async for ev in fb(req.persona):
                    yield ev
            else:
                yield {"type": "final",
                       "answer": f"The live agent hit an error: `{e.__class__.__name__}: {str(e)[:200]}`. "
                                 "Try again, or use a suggested scenario chip.",
                       "trace": [], "charts": [], "citations": [], "actions": [],
                       "usage": None, "model": None}

    return _ndjson(run_with_fallback())
