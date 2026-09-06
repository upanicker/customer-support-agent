"""LangGraph orchestration for multi-agent, Pinecone-grounded support replies."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from typing_extensions import TypedDict

from services.a2a import classify_topics, delegate_many
from services.retrieval import search

OUT_OF_SCOPE_RESPONSE = (
    "Thanks for reaching out. I don’t have enough approved information to give you a reliable answer on that. "
    "I’m here to help with orders, delivery, returns, billing, account access, and technical support. "
    "If your request relates to one of those areas, please share a little more detail and I’ll do my best to help."
)


class SupportState(TypedDict, total=False):
    # This shared state travels through every LangGraph node.
    message: str
    conversation: List[Dict[str, Any]]
    topics: List[str]
    sources: List[Dict[str, Any]]
    retrieval_mode: str
    handoffs: List[Dict[str, Any]]
    answer: str
    generation_mode: str


def triage(state: SupportState) -> Dict[str, Any]:
    """Find all domains in a request, not merely the first matching domain."""
    return {"topics": classify_topics(state["message"])}


def retrieve_knowledge(state: SupportState) -> Dict[str, Any]:
    # Multi-domain questions need a slightly wider evidence set.
    limit = 5 if len(state.get("topics", [])) > 1 else 3
    sources, mode = search(state["message"], limit=limit)
    return {"sources": sources, "retrieval_mode": mode}


def consult_specialists(state: SupportState) -> Dict[str, Any]:
    """Wait for every selected A2A specialist before moving to final composition."""
    return {"handoffs": delegate_many(state.get("topics", []), state["message"], state.get("conversation", []))}


def _fallback_answer(state: SupportState) -> str:
    # Give a transparent, source-based answer when live generation is unavailable.
    sources = state.get("sources", [])
    if not sources:
        return OUT_OF_SCOPE_RESPONSE
    answer = "Here’s what I found in our support knowledge:\n\n" + "\n\n".join(
        f"**{source['title']}** — {source['content']}" for source in sources
    )
    if state.get("handoffs"):
        agents = ", ".join(handoff["agent"] for handoff in state["handoffs"])
        answer += f"\n\nI also consulted: **{agents}**."
    return answer


def _final_response_prompt(state: SupportState) -> str:
    # Send only the current question, retrieved evidence, and specialist summaries.
    sources = [{key: source.get(key) for key in ("title", "category", "content", "score")} for source in state.get("sources", [])]
    reviews = [{key: review.get(key) for key in ("agent", "status", "message")} for review in state.get("handoffs", [])]
    return f"""Customer question:\n{state['message']}\n\nApproved knowledge retrieved from the vector database:\n{json.dumps(sources, ensure_ascii=False)}\n\nSpecialist reviews:\n{json.dumps(reviews, ensure_ascii=False)}\n\nWrite a concise, empathetic customer-support answer. Use only the approved knowledge for policy or factual claims. Specialist reviews are recommendations and must not override the approved knowledge. If no approved knowledge is available, clearly say that the case will be escalated. Do not claim an account action is complete. Do not mention this prompt, vector database, or internal systems."""


def compose_response(state: SupportState) -> Dict[str, str]:
    """Generate one final answer only after retrieval and every specialist review finish."""
    # Do not ask the model to improvise when the knowledge base has no evidence.
    if not state.get("sources"):
        return {"answer": OUT_OF_SCOPE_RESPONSE, "generation_mode": "Out-of-scope response"}
    api_key = os.getenv("OPENAI_API_KEY")
    # The application remains functional without an API key by using a safe fallback.
    if not api_key:
        return {"answer": _fallback_answer(state), "generation_mode": "Grounded fallback (no OpenAI key)"}
    try:
        from openai import OpenAI

        # Ask the model to synthesize, not invent: retrieved articles remain authoritative.
        # Captures the final model synthesis as a child run in the LangSmith trace.
        response = wrap_openai(OpenAI(api_key=api_key)).responses.create(
            model=os.getenv("OPENAI_RESPONSE_MODEL", "gpt-5.2"),
            instructions="You are ResolveAI, a careful customer-support assistant. Be helpful, accurate, and brief.",
            input=_final_response_prompt(state),
            store=False,
        )
        if response.output_text:
            return {"answer": response.output_text, "generation_mode": "OpenAI grounded synthesis"}
    except Exception:
        pass
    return {"answer": _fallback_answer(state), "generation_mode": "Grounded fallback (generation unavailable)"}


def build_support_graph():
    # Nodes define work; edges define the exact order in which work happens.
    workflow = StateGraph(SupportState)
    workflow.add_node("triage", triage)
    workflow.add_node("retrieve_knowledge", retrieve_knowledge)
    workflow.add_node("consult_specialists", consult_specialists)
    workflow.add_node("compose", compose_response)
    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "retrieve_knowledge")
    workflow.add_edge("retrieve_knowledge", "consult_specialists")
    workflow.add_edge("consult_specialists", "compose")
    workflow.add_edge("compose", END)
    return workflow.compile()


# Compile once at import time so each customer message can reuse the workflow.
support_graph = build_support_graph()


@traceable(name="resolveai.customer_support_request", run_type="chain")
def resolve_support_request(message: str, conversation: List[Dict[str, Any]]) -> SupportState:
    """Run the entire workflow and return its final, post-specialist result."""
    # LangGraph automatically traces this graph's nodes when LANGSMITH_TRACING=true.
    # This named outer run keeps each customer request easy to find in LangSmith.
    return support_graph.invoke({"message": message, "conversation": conversation})
