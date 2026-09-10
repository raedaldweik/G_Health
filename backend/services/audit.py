"""Governance audit trail, every agent tool call, consent denial, model score and
human decision is logged. Held in memory and persisted as compact JSON, so a log
write on the agent's hot path costs microseconds, not a re-read and pretty-print
of the whole file. Surfaced on the Audit page and linked from each answer's
governance record."""
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

_items: list[dict] | None = None      # newest first; loaded from disk once


def _ensure_loaded() -> list[dict]:
    global _items
    if _items is None:
        if AUDIT_FILE.exists():
            try:
                _items = json.loads(AUDIT_FILE.read_text())
            except Exception:
                _items = []
        else:
            _items = []
    return _items


def log(event_type: str, actor: str, detail: str, patient_id: str = "", severity: str = "info"):
    entry = {
        "id": f"aud-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type, "actor": actor,
        "detail": detail[:400], "patient_id": patient_id, "severity": severity,
    }
    with _lock:
        items = _ensure_loaded()
        items.insert(0, entry)
        del items[MAX_ENTRIES:]
        _save(items)
    return entry


def _save(items: list[dict]):
    RUNTIME.mkdir(parents=True, exist_ok=True)
    AUDIT_FILE.write_text(json.dumps(items, separators=(",", ":")))


def list_entries(limit: int = 200) -> list[dict]:
    with _lock:
        return list(_ensure_loaded()[:limit])


def entries_since(iso_ts: str, limit: int = 60) -> list[dict]:
    """Entries logged at or after iso_ts (newest first): the audit slice of one
    answer's governance record."""
    with _lock:
        items = _ensure_loaded()
        out = []
        for e in items:
            if e.get("timestamp", "") < iso_ts:
                break
            out.append(e)
            if len(out) >= limit:
                break
        return out
