"""Chat API, streams NDJSON events (live agent steps → final payload).

Every final payload leaves this router with a `governance` record attached: the
controls that were in force for that answer (grounding, consent, human
oversight, data boundary, model transparency) plus the audit entries the turn
wrote, computed by services.governance from the turn's own artefacts."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import agent, governance, scenarios

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


def _with_governance(gen):
    """Attach the per-answer governance record to every final event that lacks one."""
    since = datetime.now(timezone.utc).isoformat()

    async def wrapped():
        async for ev in gen:
            if isinstance(ev, dict) and ev.get("type") == "final" and "governance" not in ev:
                try:
                    ev = {**ev, "governance": governance.build(ev, since)}
                except Exception:            # a governance failure must never lose the answer
                    pass
            yield ev
    return wrapped()


def _ndjson(gen):
    async def stream():
        async for ev in gen:
            yield json.dumps(ev, default=str) + "\n"
    return StreamingResponse(stream(), media_type="application/x-ndjson")


NO_KEY_NOTICE = (
    "**Free-form questions need the language-model credentials configured on the server.** "
    "The suggested scenario chips run fully against the live data without them. To enable "
    "free-form chat, add the model credentials to the backend environment (see the README) and restart."
)


@router.post("/api/chat")
async def chat(req: ChatRequest):
    use_scripted = req.scenario_id and (not agent.llm_enabled() or FORCE_SCENARIOS)

    if use_scripted:
        runner = scenarios.get_runner(req.scenario_id)
        if runner:
            return _ndjson(_with_governance(runner(req.persona)))

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
            # Live agent failed mid-demo: fall back to the direct tool runner when we
            # have one, else surface a clean error.
            fb = scenarios.get_runner(req.scenario_id) if req.scenario_id else None
            if fb:
                yield {"type": "step", "status": "done", "agent": "system", "tool": "fallback",
                       "detail": f"live agent unavailable ({e.__class__.__name__}); running the same tools directly"}
                async for ev in fb(req.persona):
                    yield ev
            else:
                yield {"type": "final",
                       "answer": f"The live agent hit an error: `{e.__class__.__name__}: {str(e)[:200]}`. "
                                 "Try again, or use a suggested scenario chip.",
                       "trace": [], "charts": [], "citations": [], "actions": [],
                       "usage": None, "model": None}

    return _ndjson(_with_governance(run_with_fallback()))
