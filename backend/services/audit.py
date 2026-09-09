"""Governance audit trail, every agent tool call, consent denial, model score and
human decision is logged. JSON-persisted; surfaced on the Audit page."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent.parent / "data" / "runtime"
AUDIT_FILE = RUNTIME / "audit.json"
_lock = threading.Lock()
MAX_ENTRIES = 800


def log(event_type: str, actor: str, detail: str, patient_id: str = "", severity: str = "info"):
    entry = {
        "id": f"aud-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type, "actor": actor,
        "detail": detail[:400], "patient_id": patient_id, "severity": severity,
    }
    with _lock:
        items = _load()
        items.insert(0, entry)
        _save(items[:MAX_ENTRIES])
    return entry


def _load() -> list[dict]:
    if AUDIT_FILE.exists():
        try:
            return json.loads(AUDIT_FILE.read_text())
        except Exception:
            return []
    return []


def _save(items: list[dict]):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    AUDIT_FILE.write_text(json.dumps(items, indent=2))


def list_entries(limit: int = 200) -> list[dict]:
    return _load()[:limit]
