"""Embed the bundled knowledge articles and upsert them into Pinecone."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

load_dotenv()
INDEX_NAME = os.environ["PINECONE_INDEX"]
NAMESPACE = os.getenv("PINECONE_NAMESPACE", "help-center")
DOCS = json.loads((Path(__file__).parent / "data" / "demo_knowledge.json").read_text())

pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
if INDEX_NAME not in [item["name"] for item in pc.list_indexes()]:
    pc.create_index(name=INDEX_NAME, dimension=1536, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"))
    while not pc.describe_index(INDEX_NAME).status["ready"]:
        time.sleep(2)

index_description = pc.describe_index(INDEX_NAME)
INDEX_DIMENSION = getattr(index_description, "dimension", None) or index_description["dimension"]

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
embeddings = client.embeddings.create(
    model="text-embedding-3-small",
    input=[doc["content"] for doc in DOCS],
    dimensions=INDEX_DIMENSION,
).data
vectors = [{"id": doc["id"], "values": embedding.embedding,
            "metadata": {key: doc[key] for key in ("title", "content", "category")}}
           for doc, embedding in zip(DOCS, embeddings)]
pc.Index(INDEX_NAME).upsert(vectors=vectors, namespace=NAMESPACE)
print(f"Upserted {len(vectors)} articles into {INDEX_NAME}/{NAMESPACE} ({INDEX_DIMENSION}-dimension vectors).")
