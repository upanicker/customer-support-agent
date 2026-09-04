from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import requests


ROUTES = {
    "billing": ("Billing specialist", "A2A_BILLING_URL"),
    "order": ("Order specialist", "A2A_ORDERS_URL"),
    "technical": ("Technical specialist", "A2A_TECHNICAL_URL"),
}

SPECIALIST_INSTRUCTIONS = {
    "billing": "Review billing, payment, refund, invoice, and subscription issues. State only a concise next-step recommendation. Never request payment-card information.",
    "order": "Review order, delivery, tracking, cancellation, return, and item issues. State only a concise next-step recommendation. Never claim an order action is complete.",
    "technical": "Review sign-in, app, browser, outage, and error issues. State only concise diagnostic or escalation guidance.",
}

# Keyword groups map a customer message to one or more specialist domains.
TOPIC_KEYWORDS = {
    "billing": ("refund", "invoice", "charged", "payment", "subscription", "billing", "renewal"),
    "order": ("order", "delivery", "shipping", "tracking", "return", "package", "item"),
    "technical": ("error", "bug", "crash", "login", "not working", "app", "browser", "outage"),
}


def classify(message: str) -> str | None:
    topics = classify_topics(message)
    return topics[0] if topics else None


def classify_topics(message: str) -> list[str]:
    """Return every relevant support domain, allowing a request to use several agents."""
    text = message.lower()
    # A list allows one prompt to reach multiple agents, such as Orders + Billing.
    return [topic for topic, keywords in TOPIC_KEYWORDS.items() if any(keyword in text for keyword in keywords)]


def delegate(topic: str | None, message: str, context: list[dict[str, str]]) -> dict[str, Any] | None:
    if not topic:
        return None
    agent, env_key = ROUTES[topic]
    # An external URL opts into a remote A2A specialist for this domain.
    url = os.getenv(env_key)
    if not url:
        return _internal_review(topic, agent, message)
    # Limit context to the latest turns to keep handoffs focused and small.
    payload = {"message": {"role": "user", "parts": [{"type": "text", "text": message}]}, "context": context[-6:]}
    try:
        response = requests.post(url, json=payload, timeout=12)
        response.raise_for_status()
        data = response.json()
        return {"agent": agent, "status": "connected", "message": data.get("text") or data.get("result", "Specialist response received.")}
    except requests.RequestException as exc:
        return {"agent": agent, "status": "unavailable", "message": f"Specialist endpoint could not be reached: {exc}"}


def _internal_review(topic: str, agent: str, message: str) -> dict[str, Any]:
    """A scoped built-in specialist used until an external A2A endpoint is configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"agent": agent, "status": "simulated", "message": f"{agent} reviewed this request and recommends confirming the relevant account or order details before completing any action."}
    try:
        from openai import OpenAI

        response = OpenAI(api_key=api_key).responses.create(
            model=os.getenv("OPENAI_SPECIALIST_MODEL", os.getenv("OPENAI_RESPONSE_MODEL", "gpt-5.2")),
            instructions=f"You are the {agent}. {SPECIALIST_INSTRUCTIONS[topic]}",
            input=message,
            store=False,
        )
        if response.output_text:
            return {"agent": agent, "status": "internal", "message": response.output_text}
    except Exception:
        pass
    return {"agent": agent, "status": "unavailable", "message": "Specialist review is temporarily unavailable; continue with the approved support knowledge."}


def delegate_many(topics: list[str], message: str, context: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Ask all relevant specialists, then return their reviews as one completed batch."""
    if not topics:
        return []
    # Run independent specialist reviews concurrently, then wait for all results.
    with ThreadPoolExecutor(max_workers=len(topics)) as executor:
        results = list(executor.map(lambda topic: delegate(topic, message, context), topics))
    return [result for result in results if result is not None]
