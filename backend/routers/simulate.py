"""Patient what-if simulator APIs: baseline, live re-scoring, presets, and a streamed
narrated explanation of how the deployed model's estimate responded to changed inputs."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services import audit as audit_svc
from services import whatif

router = APIRouter()


class SimRequest(BaseModel):
    patient_id: str
    overrides: dict = {}
    actor: str = "clinician"


@router.get("/api/simulate/patients")
def simulate_patients(q: str = "", limit: int = 8):
    return {"presets": whatif.presets_patients(), "matches": whatif.search_patients(q, min(limit, 20))}


@router.get("/api/simulate/baseline/{patient_id}")
def simulate_baseline(patient_id: str):
    res = whatif.baseline(patient_id)
    if res.get("error"):
        raise HTTPException(404, res["error"])
    if res.get("consent") == "DENIED":
        audit_svc.log("CONSENT·DENIED", "clinician", "What-if simulator blocked on a restricted record",
                      patient_id, "warning")
    return res


@router.get("/api/simulate/preset/{patient_id}/{preset_id}")
def simulate_preset(patient_id: str, preset_id: str):
    ov = whatif.preset_overrides(preset_id, patient_id)
    if not ov:
        raise HTTPException(404, "unknown preset or patient")
    return {"overrides": ov}


@router.post("/api/simulate")
def simulate(req: SimRequest):
    res = whatif.simulate(req.patient_id, req.overrides)
    if res.get("error"):
        raise HTTPException(404, res["error"])
    return res


@router.post("/api/simulate/explain")
async def simulate_explain(req: SimRequest):
    async def stream():
        async for ev in whatif.explain(req.patient_id, req.overrides, req.actor):
            yield json.dumps(ev, default=str) + "\n"
    return StreamingResponse(stream(), media_type="application/x-ndjson")
