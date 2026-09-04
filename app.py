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
  :root { --ink:#172033; --muted:#64748b; --line:#dbe4f0; --canvas:#f6f8fc; --brand:#4659d9; --tint:#eef1ff; }
  .stApp { background:var(--canvas); color:var(--ink); }
  [data-testid='stAppViewContainer'] { background:var(--canvas); }
  .block-container { max-width:1180px; padding-top:2.35rem; padding-bottom:7rem; }
  [data-testid='stSidebar'] { background:#ffffff; border-right:1px solid var(--line); }
  [data-testid='stSidebar'] > div:first-child { padding-top:1.5rem; }
  [data-testid='stSidebar'] * { color:var(--ink); }
  [data-testid='stSidebar'] .stCaption { color:var(--muted) !important; }
  [data-testid='stSidebar'] .stRadio label { padding:.35rem .15rem; font-weight:550; }
  .hero { padding:.35rem 0 1.3rem; max-width:760px; }
  .hero h1 { margin:0; font-size:2.5rem; color:var(--ink); letter-spacing:-.055em; line-height:1.1; }
  .hero p { color:var(--muted); margin:.65rem 0 0; font-size:1.05rem; line-height:1.6; }
  .eyebrow { color:#4054c8; font-size:.75rem; font-weight:800; letter-spacing:.13em; }
  .metric-card { border:1px solid var(--line); border-radius:16px; padding:1.05rem 1.1rem; background:#ffffff; box-shadow:0 3px 12px rgba(30,41,59,.04); }
  .metric-card div { color:var(--muted); font-size:.73rem; font-weight:750; letter-spacing:.06em; }
  .metric-card strong { color:var(--ink); font-size:1.35rem; display:block; margin-top:.3rem; }
  .source { border:1px solid #d9e4ff; border-left:4px solid #6376e8; background:#f6f8ff; color:var(--ink); padding:.8rem .9rem; border-radius:10px; margin:.55rem 0; line-height:1.45; }
  .agent-pill { display:inline-block; margin-top:.45rem; padding:.25rem .55rem; border-radius:999px; background:#e9fbf2; color:#16734e; font-size:.78rem; font-weight:650; }
  [data-testid='stChatMessage'] { background:#ffffff; border:1px solid var(--line); border-radius:16px; padding:.9rem 1rem; box-shadow:0 2px 8px rgba(30,41,59,.035); }
  [data-testid='stChatMessage'] p { color:var(--ink); line-height:1.55; }
  [data-testid='stChatInput'] { background:#ffffff; border:1px solid var(--line); border-radius:16px; box-shadow:0 -4px 18px rgba(30,41,59,.05); }
  [data-testid='stChatInput'] textarea { color:var(--ink) !important; }
  .stButton > button { border-radius:10px; border:1px solid #cfd8ef; color:#3547be; background:#f7f8ff; font-weight:650; }
  .stButton > button:hover { border-color:#7282df; background:var(--tint); color:#2e40b5; }
  div[data-testid='stAlert'] { border-radius:10px; }
  .stMarkdown, .stMarkdown p, label, [data-testid='stMetricValue'] { color:var(--ink); }
  hr { border-color:var(--line) !important; }
</style>""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi, I’m ResolveAI. I can help with orders, billing, returns, account access, and technical issues. What can I resolve for you?", "sources": [], "handoffs": []}]
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
        rankdir=LR; bgcolor=\"transparent\"; node [shape=box style=\"rounded,filled\" fillcolor=\"#ffffff\" fontcolor=\"#172033\" color=\"#bfccec\"]; edge [color=\"#7586dd\"];
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
    st.caption("Add a short summary, choose a priority, then select **Create support ticket**.")
    with st.form("ticket_form", clear_on_submit=True):
        summary = st.text_input("Issue summary", placeholder="e.g. Refund still pending after 10 business days")
        priority = st.select_slider("Priority", options=["Low", "Normal", "High", "Urgent"], value="Normal")
        submitted = st.form_submit_button("Create support ticket", type="primary", use_container_width=True)
    if submitted:
        clean_summary = summary.strip()
        if not clean_summary:
            st.warning("Enter an issue summary before creating the ticket.")
        else:
            ticket = {"id": f"SUP-{str(uuid.uuid4())[:6].upper()}", "summary": clean_summary, "priority": priority, "created": datetime.now().strftime("%H:%M")}
            st.session_state.tickets.append(ticket)
            st.success(f"Ticket {ticket['id']} created and queued for human support.")
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
            for handoff in msg.get("handoffs", []):
                st.markdown(f"<span class='agent-pill'>↗ {handoff['agent']} · {handoff['status']}</span>", unsafe_allow_html=True)
            for source in msg.get("sources", []):
                score = source.get("score", 0)
                score_label = f"{score * 100:.0f}% match" if isinstance(score, (int, float)) else "Match unavailable"
                st.markdown(f"<div class='source'><b>{source['title']}</b> · {source['category']} · <b>{score_label}</b><br><small>{source['content']}</small></div>", unsafe_allow_html=True)
    if prompt := st.chat_input("Describe your issue…"):
        st.session_state.messages.append({"role": "user", "content": prompt, "sources": [], "handoffs": []})
        with st.chat_message("user"): st.write(prompt)
        result = resolve_support_request(prompt, st.session_state.messages)
        sources, handoffs = result.get("sources", []), result.get("handoffs", [])
        st.session_state.handoffs.extend(handoffs)
        response = result["answer"]
        st.session_state.messages.append({"role": "assistant", "content": response, "sources": sources, "handoffs": handoffs})
        st.rerun()
