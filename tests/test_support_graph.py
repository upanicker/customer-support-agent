from services.support_graph import resolve_support_request


def test_graph_routes_billing_request_to_specialist(monkeypatch):
    # With no external endpoint, the test exercises the built-in/simulated specialist path.
    monkeypatch.delenv("A2A_BILLING_URL", raising=False)
    result = resolve_support_request("My subscription payment failed", [])
    assert result["handoffs"][0]["agent"] == "Billing specialist"
    assert "Failed subscription renewal" in result["answer"]


def test_graph_consults_all_relevant_specialists(monkeypatch):
    # One customer sentence can require more than one domain specialist.
    monkeypatch.delenv("A2A_BILLING_URL", raising=False)
    monkeypatch.delenv("A2A_ORDERS_URL", raising=False)
    result = resolve_support_request("My order is late and I was charged twice", [])
    assert {handoff["agent"] for handoff in result["handoffs"]} == {"Billing specialist", "Order specialist"}


def test_graph_returns_diplomatic_message_when_knowledge_has_no_match(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.delenv("PINECONE_INDEX", raising=False)
    result = resolve_support_request("Write a poem about the moon", [])
    assert result["generation_mode"] == "Out-of-scope response"
    assert "Thanks for reaching out" in result["answer"]
