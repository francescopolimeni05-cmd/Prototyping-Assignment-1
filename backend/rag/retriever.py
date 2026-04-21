"""
Retrieval interface consumed by the chat service.

Embeds the query, pulls top-k from Chroma, returns a list of dicts
{source, score, text}. If the collection is empty or embeddings fail we
return [] — callers treat that as "no retrieval, answer anyway".
"""
from __future__ import annotations

from typing import Any

from .. import config
from ..services.openai_client import embed
from .store import get_collection


def retrieve(query: str, destination_hint: str = "", k: int | None = None) -> list[dict[str, Any]]:
    if not query.strip():
        return []
    k = k or config.RAG_TOP_K

    try:
        vec = embed([query])[0]
    except Exception:
        return []

    coll = get_collection()
    if coll.count() == 0:
        return []

    # Simple metadata boost: if a destination hint is present, pre-filter
    # to chunks whose `city` metadata matches (case-insensitive).
    # The trip_context from the client usually starts with "TRIP: <City>, ..."
    # so we strip the "TRIP:" prefix before splitting.
    where: dict | None = None
    hint_raw = destination_hint or ""
    if hint_raw.lower().startswith("trip:"):
        hint_raw = hint_raw.split(":", 1)[1]
    hint = hint_raw.split(",")[0].strip().lower() if hint_raw else ""
    if hint:
        # Chroma's `where` supports exact match; we index `city_lower`.
        where = {"city_lower": {"$eq": hint}}

    res = None
    if where is not None:
        try:
            res = coll.query(
                query_embeddings=[vec],
                n_results=k,
                where=where,
            )
            # If the filter matched nothing, fall through to unfiltered.
            docs0 = (res.get("documents") or [[]])[0]
            if not docs0:
                res = None
        except Exception:
            res = None

    if res is None:
        # Unfiltered semantic search — relevant when the user asks about a
        # different city than the one in their trip setup, or when the
        # destination isn't in the indexed KB.
        try:
            res = coll.query(query_embeddings=[vec], n_results=k)
        except Exception:
            return []

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    chunks = []
    for text, meta, dist in zip(docs, metas, dists):
        chunks.append({
            "text": text,
            "source": meta.get("source", "unknown"),
            "score": float(1.0 - dist) if dist is not None else 0.0,
        })
    return chunks
