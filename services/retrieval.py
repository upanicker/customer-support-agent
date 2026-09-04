from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


# Bundled knowledge provides an offline fallback when Pinecone is not configured.
DATA_PATH = Path(__file__).parents[1] / "data" / "demo_knowledge.json"
STOP_WORDS = {"a", "an", "and", "are", "can", "does", "for", "how", "i", "in", "is", "it", "my", "of", "the", "to", "what", "when", "will", "with"}


def _tokens(text: str) -> set[str]:
    # Normalize text into comparable words for the lightweight local search.
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if token not in STOP_WORDS}


def _local_search(query: str, limit: int = 3) -> list[dict[str, Any]]:
    # This fallback is deliberately simple; production retrieval uses vectors.
    docs = json.loads(DATA_PATH.read_text())
    query_terms = _tokens(query)
    scored = []
    for doc in docs:
        # Title words are stronger signals than incidental matches in article text.
        score = 2 * len(query_terms & _tokens(doc["title"])) + len(query_terms & _tokens(doc["content"]))
        if score:
            scored.append((score, doc))
    return [doc | {"score": score / max(len(query_terms), 1), "source": "Demo knowledge base"}
            for score, doc in sorted(scored, reverse=True, key=lambda item: item[0])[:limit]]


def search(query: str, limit: int = 3) -> tuple[list[dict[str, Any]], str]:
    """Retrieve from Pinecone if enabled; otherwise return an inspectable local fallback."""
    key, index_name = os.getenv("PINECONE_API_KEY"), os.getenv("PINECONE_INDEX")
    # Keep the app usable in local demo mode when credentials are absent.
    if not (key and index_name):
        return _local_search(query, limit), "Local demo retrieval"

    try:
        from pinecone import Pinecone
        from openai import OpenAI

        # Query embeddings must have the same dimension as the target index.
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
        # Convert Pinecone match objects into UI-friendly dictionaries.
        matches = []
        for match in result.matches:
            meta = match.metadata or {}
            matches.append({"id": match.id, "title": meta.get("title", "Knowledge article"),
                            "content": meta.get("content", ""), "category": meta.get("category", "General"),
                            "score": match.score, "source": "Pinecone"})
        return matches, "Pinecone retrieval"
    except Exception:
        # Network or configuration failures should not break the customer chat.
        return _local_search(query, limit), "Local fallback (Pinecone unavailable)"
