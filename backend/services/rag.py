"""
Nabd, grounded retrieval over the national clinical guideline corpus.

Pure keyword retrieval: a BM25 index over page-level chunks of the guideline
PDFs. Zero external dependencies, zero network calls on the query path, fully
deterministic — a search is a ranking over an in-memory index and returns in
microseconds.

Every hit carries document, page and a snippet so the agent can cite
"MOPH T2DM guideline, p. 44" and the UI can open the source passage.
On Google Cloud: Vertex AI RAG Engine (managed corpus), same search contract.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.ERROR)   # cosmetic font warnings on MOPH PDFs

import numpy as np
from rank_bm25 import BM25Okapi

BASE = Path(__file__).resolve().parent.parent
GUIDELINES = BASE / "data" / "guidelines"
RUNTIME = BASE / "data" / "runtime"

CHUNK_CHARS = 1400
OVERLAP = 200

_lock = threading.Lock()
_state: dict = {"chunks": [], "bm25": None}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _corpus_hash() -> str:
    h = hashlib.sha256()
    for p in sorted(GUIDELINES.glob("*.pdf")):
        h.update(p.name.encode())
        h.update(str(p.stat().st_size).encode())
    return h.hexdigest()[:16]


def _extract_chunks() -> list[dict]:
    """PDF → page texts → overlapping chunks. Cached to disk keyed by corpus hash."""
    cache = RUNTIME / f"ragchunks-{_corpus_hash()}.json"
    if cache.exists():
        try:
            return json.loads(cache.read_text())
        except Exception:
            pass
    from pypdf import PdfReader
    chunks = []
    for pdf in sorted(GUIDELINES.glob("*.pdf")):
        doc = pdf.stem.replace("_", " ")
        try:
            reader = PdfReader(str(pdf))
        except Exception:
            continue
        for pageno, page in enumerate(reader.pages, start=1):
            try:
                text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
            except Exception:
                continue
            if len(text) < 80:
                continue
            i = 0
            while i < len(text):
                piece = text[i:i + CHUNK_CHARS]
                chunks.append({"doc": doc, "file": pdf.name, "page": pageno, "text": piece})
                i += CHUNK_CHARS - OVERLAP
    RUNTIME.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(chunks))
    return chunks


def ensure_loaded():
    with _lock:
        if _state["bm25"] is not None:
            return
        chunks = _extract_chunks()
        _state["chunks"] = chunks
        _state["bm25"] = BM25Okapi([_tokenize(c["text"]) for c in chunks]) if chunks else None


def search(query: str, top_k: int = 4) -> list[dict]:
    ensure_loaded()
    chunks, bm25 = _state["chunks"], _state["bm25"]
    if not chunks:
        return []
    scores = np.array(bm25.get_scores(_tokenize(query)))
    if scores.max() > 0:
        scores = scores / scores.max()
    idx = np.argsort(-scores)[:top_k]
    hits = []
    for i in idx:
        if scores[int(i)] <= 0:
            continue
        c = chunks[int(i)]
        hits.append({"doc": c["doc"], "file": c["file"], "page": c["page"],
                     "snippet": c["text"][:700], "score": round(float(scores[int(i)]), 3),
                     "retrieval": "bm25"})
    return hits


def list_documents() -> list[dict]:
    ensure_loaded()
    byfile: dict[str, dict] = {}
    for c in _state["chunks"]:
        d = byfile.setdefault(c["file"], {"file": c["file"], "doc": c["doc"],
                                          "pages": 0, "chunks": 0})
        d["pages"] = max(d["pages"], c["page"])
        d["chunks"] += 1
    docs = sorted(byfile.values(), key=lambda d: d["file"])
    for d in docs:
        d["size_mb"] = round((GUIDELINES / d["file"]).stat().st_size / 1048576, 2)
    return docs


def status() -> dict:
    ensure_loaded()
    return {"documents": len(list_documents()), "chunks": len(_state["chunks"]),
            "retrieval": "keyword", "index": "BM25", "corpus_hash": _corpus_hash()}
