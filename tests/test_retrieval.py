from services.retrieval import search


def test_local_knowledge_returns_refund_article(monkeypatch):
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.delenv("PINECONE_INDEX", raising=False)
    results, mode = search("How long will my refund take?")
    assert mode == "Local demo retrieval"
    assert any(item["id"] == "refund-timing" for item in results)
