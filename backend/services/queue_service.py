"""Human-in-the-loop queue, drafted actions awaiting clinician sign-off.

Nothing the agent drafts ever reaches the (synthetic) EMR: items sit here until a
human approves, edits, or rejects them. JSON-persisted so demo state survives restarts.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent / "data" / "runtime"
QUEUE_FILE = RUNTIME / "queue.json"
_lock = threading.Lock()


def _load() -> list[dict]:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except Exception:
            return []
    return []


def _save(items: list[dict]):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(items, indent=2))


def add_draft(action_type: str, title: str, detail: str, patient_id: str = "",
              patient_ids: list[str] | None = None, citation: str = "",
              drafted_by: str = "action_agent") -> dict:
    item = {
        "id": f"draft-{uuid.uuid4().hex[:8]}",
        "type": action_type, "title": title, "detail": detail[:600],
        "patient_id": patient_id, "patient_ids": patient_ids or [],
        "citation": citation, "drafted_by": drafted_by,
        "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        items = _load()
        items.insert(0, item)
        _save(items)
    return item


def list_items(status: str | None = None) -> list[dict]:
    items = _load()
    return [i for i in items if status is None or i["status"] == status]


def resolve(item_id: str, decision: str, decided_by: str = "clinician") -> dict | None:
    assert decision in ("approved", "rejected")
    with _lock:
        items = _load()
        for i in items:
            if i["id"] == item_id:
                i["status"] = decision
                i["decided_by"] = decided_by
                i["decided_at"] = datetime.now(timezone.utc).isoformat()
                _save(items)
                return i
    return None
