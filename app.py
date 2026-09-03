from __future__ import annotations

import os
import uuid
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from services.support_graph import resolve_support_request

load_dotenv()
st.set_page_config(page_title="ResolveAI", page_icon="✦", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
  .stApp { background: #09111f; color: #e7edf7; }
  [data-testid='stSidebar'] { background: #0d1728; border-right: 1px solid #22344f; }
  .hero { padding: 1.4rem 0 .5rem; } .hero h1 { margin:0; font-size:2.25rem; letter-spacing:-.06em; }
  .hero p { color:#9cafc9; margin:.4rem 0; } .eyebrow { color:#78e4c0; font-size:.78rem; font-weight:700; letter-spacing:.12em; }
  .metric-card { border:1px solid #253954; border-radius:14px; padding:1rem; background:#101d31; }
  .metric-card div { color:#91a5c1; font-size:.8rem; } .metric-card strong { font-size:1.45rem; }
  .source { border-left:3px solid #64d7b0; background:#10243a; padding:.7rem .85rem; border-radius:0 8px 8px 0; margin:.35rem 0; }
  .agent-pill { color:#78e4c0; font-size:.82rem; } .stChatMessage { background:#101d31; border-radius:14px; }
</style>""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi, I’m ResolveAI. I can help with orders, billing, returns, account access, and technical issues. What can I resolve for you?", "sources": [], "handoff": None}]
if "tickets" not in st.session_state: st.session_state.tickets = []
if "handoffs" not in st.session_state: st.session_state.handoffs = []

with st.sidebar:
    st.markdown("## ✦ ResolveAI")
    st.caption("Customer support intelligence")
    st.divider()
    page = st.radio("Workspace", ["Customer conversation", "Operations desk", "Architecture"], label_visibility="collapsed")
    st.divider()
    st.markdown("**SYSTEM STATUS**")
    st.success("● RAG online")
    st.caption("Pinecone connected" if os.getenv("PINECONE_API_KEY") else "Demo knowledge mode")
    st.info("↗ A2A router ready")
    if st.button("New conversation", use_container_width=True):
        st.session_state.messages = st.session_state.messages[:1]
        st.rerun()

if page == "Architecture":
    st.markdown("<div class='hero'><div class='eyebrow'>SOLUTION DESIGN</div><h1>Grounded resolution, coordinated agents.</h1><p>Each response is traceable to knowledge, with specialists engaged only when their expertise is needed.</p></div>", unsafe_allow_html=True)
    st.graphviz_chart("""digraph {
        rankdir=LR; bgcolor=\"#09111f\"; node [shape=box style=\"rounded,filled\" fillcolor=\"#101d31\" fontcolor=\"#e7edf7\" color=\"#64d7b0\"]; edge [color=\"#8ca6c9\"];
        Customer -> \"Streamlit experience\" -> \"Conversation orchestrator\";
        \"Conversation orchestrator\" -> \"RAG retriever\" -> \"Pinecone vector database\";
        \"Conversation orchestrator\" -> \"Grounded response + citations\";
        \"Conversation orchestrator\" -> \"A2A router\";
        \"A2A router\" -> \"Billing agent\"; \"A2A router\" -> \"Order agent\"; \"A2A router\" -> \"Technical agent\";
        \"Conversation orchestrator\" -> \"Ticket & escalation queue\";
    }""")
    c1, c2, c3 = st.columns(3)
    c1.markdown("### 01 · Understand\nIntent routing and sentiment-aware escalation keep the conversation on the right path.")
    c2.markdown("### 02 · Ground\nSemantic retrieval supplies approved knowledge and visible evidence for every answer.")
    c3.markdown("### 03 · Act\nA2A delegates work to bounded specialist agents; unresolved work becomes a ticket.")
    st.info("Production guardrail: restrict agents to scoped actions, validate customer identity before account changes, and log every tool and A2A decision.")
elif page == "Operations desk":
    st.markdown("<div class='hero'><div class='eyebrow'>SUPPORT OPERATIONS</div><h1>Resolution control room</h1><p>Monitor specialist handoffs and create human escalations.</p></div>", unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.markdown(f"<div class='metric-card'><div>OPEN TICKETS</div><strong>{len(st.session_state.tickets)}</strong></div>", unsafe_allow_html=True)
    b.markdown(f"<div class='metric-card'><div>AGENT HANDOFFS</div><strong>{len(st.session_state.handoffs)}</strong></div>", unsafe_allow_html=True)
    c.markdown("<div class='metric-card'><div>KNOWLEDGE COVERAGE</div><strong>92%</strong></div>", unsafe_allow_html=True)
    st.markdown("### Create escalation")
    with st.form("ticket"):
        summary = st.text_input("Issue summary", placeholder="e.g. Refund still pending after 10 business days")
        priority = st.select_slider("Priority", options=["Low", "Normal", "High", "Urgent"], value="Normal")
        if st.form_submit_button("Create support ticket") and summary:
            st.session_state.tickets.append({"id": f"SUP-{str(uuid.uuid4())[:6].upper()}", "summary": summary, "priority": priority, "created": datetime.now().strftime("%H:%M")})
            st.success("Escalation created and queued for a human support specialist.")
    if st.session_state.tickets:
        st.markdown("### Active tickets")
        st.dataframe(st.session_state.tickets, use_container_width=True, hide_index=True)
    if st.session_state.handoffs:
        st.markdown("### Recent A2A activity")
        for h in reversed(st.session_state.handoffs): st.markdown(f"<div class='source'><b>{h['agent']}</b> · {h['status']}<br>{h['message']}</div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='hero'><div class='eyebrow'>CUSTOMER CONVERSATION</div><h1>How can we help?</h1><p>AI answers are grounded in your support knowledge and can route work to specialist agents.</p></div>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.markdown("<div class='metric-card'><div>RESPONSE MODE</div><strong>Grounded RAG</strong></div>", unsafe_allow_html=True)
    m2.markdown("<div class='metric-card'><div>AVAILABLE AGENTS</div><strong>3 specialists</strong></div>", unsafe_allow_html=True)
    m3.markdown("<div class='metric-card'><div>AVERAGE RESPONSE</div><strong>&lt; 3 sec</strong></div>", unsafe_allow_html=True)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg.get("handoff"): st.markdown(f"<span class='agent-pill'>↗ Routed to {msg['handoff']['agent']} · {msg['handoff']['status']}</span>", unsafe_allow_html=True)
            for source in msg.get("sources", []): st.markdown(f"<div class='source'><b>{source['title']}</b> · {source['category']}<br><small>{source['content']}</small></div>", unsafe_allow_html=True)
    if prompt := st.chat_input("Describe your issue…"):
        st.session_state.messages.append({"role": "user", "content": prompt, "sources": [], "handoff": None})
        with st.chat_message("user"): st.write(prompt)
        result = resolve_support_request(prompt, st.session_state.messages)
        sources, handoff = result.get("sources", []), result.get("handoff")
        if handoff: st.session_state.handoffs.append(handoff)
        response = result["answer"]
        st.session_state.messages.append({"role": "assistant", "content": response, "sources": sources, "handoff": handoff})
        st.rerun()
