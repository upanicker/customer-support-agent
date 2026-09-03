from __future__ import annotations

import os
from typing import Any

import requests


ROUTES = {
    "billing": ("Billing specialist", "A2A_BILLING_URL"),
    "order": ("Order specialist", "A2A_ORDERS_URL"),
    "technical": ("Technical specialist", "A2A_TECHNICAL_URL"),
}


def classify(message: str) -> str | None:
    text = message.lower()
    if any(w in text for w in ("refund", "invoice", "charged", "payment", "subscription", "billing")):
        return "billing"
    if any(w in text for w in ("order", "delivery", "shipping", "tracking", "return")):
        return "order"
    if any(w in text for w in ("error", "bug", "crash", "login", "not working", "app")):
        return "technical"
    return None


def delegate(topic: str | None, message: str, context: list[dict[str, str]]) -> dict[str, Any] | None:
    if not topic:
        return None
    agent, env_key = ROUTES[topic]
    url = os.getenv(env_key)
    if not url:
        return {"agent": agent, "status": "simulated", "message": f"{agent} reviewed this request and recommends confirming the account or order details before completing the action."}
    payload = {"message": {"role": "user", "parts": [{"type": "text", "text": message}]}, "context": context[-6:]}
    try:
        response = requests.post(url, json=payload, timeout=12)
        response.raise_for_status()
        data = response.json()
        return {"agent": agent, "status": "connected", "message": data.get("text") or data.get("result", "Specialist response received.")}
    except requests.RequestException as exc:
        return {"agent": agent, "status": "unavailable", "message": f"Specialist endpoint could not be reached: {exc}"}
