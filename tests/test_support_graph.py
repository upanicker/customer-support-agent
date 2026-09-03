from services.support_graph import resolve_support_request


def test_graph_routes_billing_request_to_specialist(monkeypatch):
    monkeypatch.delenv("A2A_BILLING_URL", raising=False)
    result = resolve_support_request("My subscription payment failed", [])
    assert result["handoff"]["agent"] == "Billing specialist"
    assert "Failed subscription renewal" in result["answer"]
