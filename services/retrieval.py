from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).parents[1] / "data" / "demo_knowledge.json"


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def _local_search(query: str, limit: int = 3) -> list[dict[str, Any]]:
    docs = json.loads(DATA_PATH.read_text())
    query_terms = _tokens(query)
    scored = []
    for doc in docs:
        score = len(query_terms & _tokens(f"{doc['title']} {doc['content']}"))
        if score:
            scored.append((score, doc))
    return [doc | {"score": score / max(len(query_terms), 1), "source": "Demo knowledge base"}
            for score, doc in sorted(scored, reverse=True, key=lambda item: item[0])[:limit]]


def search(query: str, limit: int = 3) -> tuple[list[dict[str, Any]], str]:
    """Retrieve from Pinecone if enabled; otherwise return an inspectable local fallback."""
    key, index_name = os.getenv("PINECONE_API_KEY"), os.getenv("PINECONE_INDEX")
    if not (key and index_name):
        return _local_search(query, limit), "Local demo retrieval"

    try:
        from pinecone import Pinecone
        from openai import OpenAI

        pinecone = Pinecone(api_key=key)
        index_description = pinecone.describe_index(index_name)
        dimension = getattr(index_description, "dimension", None) or index_description["dimension"]
        vector = OpenAI().embeddings.create(
            model="text-embedding-3-small", input=query, dimensions=dimension
        ).data[0].embedding
        result = pinecone.Index(index_name).query(
            vector=vector, top_k=limit, include_metadata=True,
            namespace=os.getenv("PINECONE_NAMESPACE", "help-center"),
        )
        matches = []
        for match in result.matches:
            meta = match.metadata or {}
            matches.append({"id": match.id, "title": meta.get("title", "Knowledge article"),
                            "content": meta.get("content", ""), "category": meta.get("category", "General"),
                            "score": match.score, "source": "Pinecone"})
        return matches, "Pinecone retrieval"
    except Exception:
        return _local_search(query, limit), "Local fallback (Pinecone unavailable)"
