"""
Nabd — grounded retrieval over the national clinical guideline corpus.

Hybrid retrieval:
  • BM25 keyword index — always available, zero external dependencies.
  • gemini-embedding-001 semantic index — built lazily in the background when a
    GEMINI_API_KEY is present, cached to disk. Hybrid score = BM25 ⊕ cosine.

Every hit carries document, page and a snippet so the agent can cite
"MOPH T2DM guideline, p. 44" and the UI can open the source passage.
Phase 2: swap for Vertex AI RAG Engine (managed corpus) — same search contract.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
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
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")

_lock = threading.Lock()
_state: dict = {"chunks": [], "bm25": None, "embeddings": None, "embed_status": "disabled"}


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


def _build_embeddings_async():
    """Compute the semantic index in the background; cache to disk."""
    from services import llm_client as LC
    if not LC.llm_available():
        return
    _state["embed_status"] = "building"

    def work():
        try:
            cache = RUNTIME / f"ragembed-{_corpus_hash()}-{EMBED_MODEL}.npz"
            if cache.exists():
                _state["embeddings"] = np.load(cache)["emb"]
                _state["embed_status"] = "ready"
                return
            client = LC.make_client()
            texts = [c["text"] for c in _state["chunks"]]
            vecs = []
            for i in range(0, len(texts), 80):
                resp = client.models.embed_content(model=EMBED_MODEL, contents=texts[i:i + 80])
                vecs.extend([e.values for e in resp.embeddings])
            emb = np.array(vecs, dtype=np.float32)
            emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
            np.savez_compressed(cache, emb=emb)
            _state["embeddings"] = emb
            _state["embed_status"] = "ready"
            print(f"✓ Semantic index ready: {len(vecs)} chunks × {emb.shape[1]} dims ({EMBED_MODEL})", flush=True)
        except Exception as e:                      # embeddings are an enhancement, never a blocker
            _state["embed_status"] = "failed"
            _state["embed_error"] = f"{e.__class__.__name__}: {str(e)[:200]}"
            print(f"✗ Semantic index failed — retrieval stays BM25-only: {_state['embed_error']}", flush=True)

    threading.Thread(target=work, daemon=True).start()


def ensure_loaded():
    with _lock:
        if _state["bm25"] is not None:
            return
        chunks = _extract_chunks()
        _state["chunks"] = chunks
        _state["bm25"] = BM25Okapi([_tokenize(c["text"]) for c in chunks]) if chunks else None
        _build_embeddings_async()


def search(query: str, top_k: int = 4) -> list[dict]:
    ensure_loaded()
    chunks, bm25 = _state["chunks"], _state["bm25"]
    if not chunks:
        return []
    scores = np.array(bm25.get_scores(_tokenize(query)))
    if scores.max() > 0:
        scores = scores / scores.max()

    emb = _state["embeddings"]
    if emb is not None:
        try:
            from services import llm_client as LC
            client = LC.make_client()
            q = client.models.embed_content(model=EMBED_MODEL, contents=[query])
            qv = np.array(q.embeddings[0].values, dtype=np.float32)
            qv /= (np.linalg.norm(qv) + 1e-9)
            cos = emb @ qv
            scores = 0.45 * scores + 0.55 * ((cos - cos.min()) / (cos.max() - cos.min() + 1e-9))
        except Exception:
            pass                                    # fall back to BM25-only silently

    idx = np.argsort(-scores)[:top_k]
    hits = []
    for i in idx:
        c = chunks[int(i)]
        hits.append({"doc": c["doc"], "file": c["file"], "page": c["page"],
                     "snippet": c["text"][:700], "score": round(float(scores[int(i)]), 3),
                     "retrieval": "hybrid" if emb is not None else "bm25"})
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
    emb = _state.get("embeddings")
    return {"documents": len(list_documents()), "chunks": len(_state["chunks"]),
            "semantic_index": _state["embed_status"], "embed_model": EMBED_MODEL,
            "vectors": int(emb.shape[0]) if emb is not None else 0,
            "dims": int(emb.shape[1]) if emb is not None else 0,
            "error": _state.get("embed_error")}
