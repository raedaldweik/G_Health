"""Build the guideline semantic index once and write it to backend/data/runtime/.

    cd backend && GEMINI_API_KEY=... python -m scripts.embed_corpus

The file (ragembed-<corpus hash>-<model>.npz, about 1.4 MB at 768 dims) is committed to
git so that Railway / Cloud Run never embed at startup and never hit an embedding quota.
Re-run only when a guideline PDF changes (the hash in the filename changes with it)."""
from __future__ import annotations

import sys

from services import rag


def main() -> int:
    from services import llm_client as LC
    if not LC.llm_available():
        print("Set GEMINI_API_KEY (or Vertex credentials) first.")
        return 1
    rag.ensure_loaded()
    cache = rag._embed_cache()
    if cache.exists():
        print(f"Cache already present: {cache.name}. Delete it to rebuild.")
        return 0
    print(f"Embedding {len(rag._state['chunks'])} chunks with {rag.EMBED_MODEL} ...")
    emb = rag.build_embeddings()
    print(f"Done: {emb.shape[0]} vectors x {emb.shape[1]} dims -> {cache}")
    print("Commit the file so deployments load it instead of embedding.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
