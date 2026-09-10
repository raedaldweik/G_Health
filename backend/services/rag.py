"""
Nabd, grounded retrieval over the national clinical guideline corpus.

Hybrid retrieval:
  • BM25 keyword index, always available, zero external dependencies.
  • gemini-embedding-001 semantic index, built lazily in the background when a
    Gemini credential is present (independent of which model runs the agent graph),
    cached to disk. Hybrid score = BM25 ⊕ cosine.

Every hit carries document, page and a snippet so the agent can cite
"MOPH T2DM guideline, p. 44" and the UI can open the source passage.
On Google Cloud: Vertex AI RAG Engine (managed corpus), same search contract.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
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


def _embed_cache() -> Path:
    return RUNTIME / f"ragembed-{_corpus_hash()}-{EMBED_MODEL}.npz"


def _load_cached_embeddings() -> bool:
    """The semantic index is computed once per corpus and kept on disk (and in git), so a
    restart or a redeploy never re-embeds. Returns True when a cache was loaded."""
    cache = _embed_cache()
    if not cache.exists():
        return False
    try:
        emb = np.load(cache)["emb"]
        if emb.shape[0] != len(_state["chunks"]):
            return False
        _state["embeddings"] = emb
        _state["embed_status"] = "ready"
        _state["embed_source"] = "cache"
        print(f"✓ Semantic index loaded from cache: {emb.shape[0]} chunks x {emb.shape[1]} dims ({EMBED_MODEL})", flush=True)
        return True
    except Exception:
        return False


def _is_quota_error(e: Exception) -> bool:
    msg = str(e)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()


def build_embeddings(batch: int = 50, dims: int = 768, verbose: bool = True) -> np.ndarray:
    """Embed every chunk with Gemini and persist the matrix. Batches are retried with
    backoff on transient errors; a quota error aborts (the cache is written by the next
    successful run). Called by the background loader and by scripts/embed_corpus.py."""
    from services import llm_client as LC
    from google.genai import types as gtypes
    client = LC.make_client()
    texts = [c["text"] for c in _state["chunks"]]
    vecs: list = []
    for i in range(0, len(texts), batch):
        for attempt in range(4):
            try:
                resp = client.models.embed_content(
                    model=EMBED_MODEL, contents=texts[i:i + batch],
                    config=gtypes.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=dims))
                vecs.extend([e.values for e in resp.embeddings])
                break
            except Exception as e:
                if _is_quota_error(e) or attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))
        if verbose:
            print(f"  embedded {min(i + batch, len(texts))}/{len(texts)} chunks", flush=True)
    emb = np.array(vecs, dtype=np.float32)
    emb /= (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    np.savez_compressed(_embed_cache(), emb=emb)
    return emb


def _build_embeddings_async(retry: int = 0):
    """Compute the semantic index in the background unless it is already cached."""
    from services import llm_client as LC
    if _load_cached_embeddings():
        return
    if not LC.gemini_available():
        _state["embed_status"] = "disabled"
        _state["embed_reason"] = "no embedding credential"
        return
    _state["embed_status"] = "building"

    def work():
        try:
            emb = build_embeddings(verbose=False)
            _state["embeddings"] = emb
            _state["embed_status"] = "ready"
            _state["embed_source"] = "built"
            _state.pop("embed_error", None)
            print(f"✓ Semantic index ready and cached: {emb.shape[0]} chunks x {emb.shape[1]} dims ({EMBED_MODEL})", flush=True)
        except Exception as e:                      # embeddings are an enhancement, never a blocker
            quota = _is_quota_error(e)
            _state["embed_status"] = "failed"
            _state["embed_reason"] = "quota" if quota else "error"
            _state["embed_error"] = f"{e.__class__.__name__}: {str(e)[:200]}"
            print(f"! Semantic index unavailable ({'embedding quota' if quota else 'error'}); retrieval stays BM25-only: "
                  f"{_state['embed_error']}", flush=True)
            # Quota windows reset; try again a few times over the next hour without blocking anything.
            if retry < 3:
                threading.Timer(900 * (retry + 1), lambda: _build_embeddings_async(retry + 1)).start()

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
            from google.genai import types as gtypes
            q = client.models.embed_content(
                model=EMBED_MODEL, contents=[query],
                config=gtypes.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=int(emb.shape[1])))
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
            "source": _state.get("embed_source"), "reason": _state.get("embed_reason"),
            "error": _state.get("embed_error")}
