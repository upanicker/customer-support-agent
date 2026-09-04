from services.support_graph import resolve_support_request


def test_graph_routes_billing_request_to_specialist(monkeypatch):
    monkeypatch.delenv("A2A_BILLING_URL", raising=False)
    result = resolve_support_request("My subscription payment failed", [])
    assert result["handoffs"][0]["agent"] == "Billing specialist"
    assert "Failed subscription renewal" in result["answer"]


def test_graph_consults_all_relevant_specialists(monkeypatch):
    monkeypatch.delenv("A2A_BILLING_URL", raising=False)
    monkeypatch.delenv("A2A_ORDERS_URL", raising=False)
    result = resolve_support_request("My order is late and I was charged twice", [])
    assert {handoff["agent"] for handoff in result["handoffs"]} == {"Billing specialist", "Order specialist"}
