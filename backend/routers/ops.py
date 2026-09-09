"""Queue (human-in-the-loop), audit, documents, and HIE data browser APIs."""
from __future__ import annotations

import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services import audit as audit_svc
from services import hie, queue_service, rag

router = APIRouter()


# ── Human-in-the-loop queue ──
@router.get("/api/queue")
def get_queue(status: str | None = None):
    return {"items": queue_service.list_items(status)}


class Decision(BaseModel):
    decided_by: str = "clinician"


@router.post("/api/queue/{item_id}/{decision}")
def decide(item_id: str, decision: str, body: Decision):
    if decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be approved|rejected")
    item = queue_service.resolve(item_id, decision, body.decided_by)
    if not item:
        raise HTTPException(404, "draft not found")
    audit_svc.log(f"HITL·{decision.upper()}", body.decided_by,
                  f"{item['type']} '{item['title']}' {decision}",
                  item.get("patient_id", ""), "action")
    return {"ok": True, "item": item}


# ── Audit trail ──
@router.get("/api/audit")
def get_audit(limit: int = 150):
    return {"entries": audit_svc.list_entries(limit)}


# ── Guideline documents ──
@router.get("/api/documents")
def documents():
    return {"documents": rag.list_documents(), "status": rag.status()}


@router.get("/api/documents/file/{name}")
def document_file(name: str):
    path = rag.GUIDELINES / name
    if not path.exists() or path.suffix != ".pdf" or "/" in name:
        raise HTTPException(404, "document not found")
    return FileResponse(path, media_type="application/pdf")


# ── HIE data browser ──
@router.get("/api/data/tables")
def data_tables():
    t = hie.tables()
    dd = hie.data_dictionary()
    from services import bq
    return {"tables": [{"name": k, "rows": len(v), "columns": list(v.columns),
                        "description": dd.get(k, "")} for k, v in t.items()],
            "source": bq.STATUS}


@router.get("/api/data/{table}")
def data_rows(table: str, offset: int = 0, limit: int = 50, search: str = ""):
    t = hie.tables()
    if table not in t:
        raise HTTPException(404, f"unknown table '{table}'")
    df = t[table]
    if search:
        mask = df.astype(str).apply(
            lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        df = df[mask]
    page = df.iloc[offset:offset + min(limit, 200)].replace({np.nan: None})
    return {"table": table, "total": int(len(df)), "offset": offset,
            "rows": page.to_dict("records")}


# ── Single patient (landing-page story card + deep links) ──
@router.get("/api/patient/{patient_id}")
def patient(patient_id: str):
    from services import ml
    rec = hie.get_patient(patient_id)
    if not rec.get("found"):
        raise HTTPException(404, "patient not found")
    if rec.get("consent") == "DENIED":
        return {"patient_id": patient_id, "consent": "DENIED"}
    rec["risk"] = ml.score_patient(patient_id)
    return rec


@router.get("/api/story/hero")
def story_hero():
    """The patient the demo follows, the highest-yield, believable deep-dive case."""
    from services import scenarios
    return patient(scenarios._pick_deepdive_patient())
