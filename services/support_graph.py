"""LangGraph workflow that orchestrates grounded support and A2A specialist work."""
from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from services.a2a import classify, delegate
from services.retrieval import search


class SupportState(TypedDict, total=False):
    message: str
    conversation: list[dict[str, str]]
    topic: str | None
    sources: list[dict[str, Any]]
    retrieval_mode: str
    handoff: dict[str, Any] | None
    answer: str


def triage(state: SupportState) -> dict[str, Any]:
    """Identify the domain that may need a specialist agent."""
    return {"topic": classify(state["message"])}


def retrieve_knowledge(state: SupportState) -> dict[str, Any]:
    sources, mode = search(state["message"])
    return {"sources": sources, "retrieval_mode": mode}


def route_to_specialist(state: SupportState) -> Literal["handoff", "compose"]:
    return "handoff" if state.get("topic") else "compose"


def a2a_handoff(state: SupportState) -> dict[str, Any]:
    """A2A boundary: calls the scoped external specialist endpoint when configured."""
    return {"handoff": delegate(state.get("topic"), state["message"], state.get("conversation", []))}


def compose_response(state: SupportState) -> dict[str, str]:
    sources = state.get("sources", [])
    if sources:
        answer = "Here’s what I found in our support knowledge:\n\n" + "\n\n".join(
            f"**{source['title']}** — {source['content']}" for source in sources
        )
    else:
        answer = "I don’t have a confident answer in the available knowledge yet. I can help create an escalation so a support specialist can investigate."
    handoff = state.get("handoff")
    if handoff:
        answer += f"\n\nI’ve also asked the **{handoff['agent']}** to review this."
    answer += f"\n\n_{state.get('retrieval_mode', 'Retrieval complete')}_"
    return {"answer": answer}


def build_support_graph():
    workflow = StateGraph(SupportState)
    workflow.add_node("triage", triage)
    workflow.add_node("retrieve_knowledge", retrieve_knowledge)
    workflow.add_node("a2a_handoff", a2a_handoff)
    workflow.add_node("compose", compose_response)
    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "retrieve_knowledge")
    workflow.add_conditional_edges("retrieve_knowledge", route_to_specialist, {"handoff": "a2a_handoff", "compose": "compose"})
    workflow.add_edge("a2a_handoff", "compose")
    workflow.add_edge("compose", END)
    return workflow.compile()


support_graph = build_support_graph()


def resolve_support_request(message: str, conversation: list[dict[str, str]]) -> SupportState:
    """Invoke the compiled workflow from Streamlit or a notebook."""
    return support_graph.invoke({"message": message, "conversation": conversation})
