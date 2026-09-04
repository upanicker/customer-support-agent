# ResolveAI — Customer Support Agent

A polished Streamlit customer-support copilot with retrieval-augmented responses, Pinecone support, ticket escalation, and LangGraph-orchestrated A2A specialist-agent handoffs.

## Run

```bash
cd "customer support agent"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

It works immediately with the bundled demo knowledge. For production retrieval and final-answer synthesis, set `OPENAI_API_KEY`, `OPENAI_RESPONSE_MODEL`, `PINECONE_API_KEY`, and `PINECONE_INDEX`, then ingest records with `title`, `content`, and `category` metadata. A2A endpoints are optional; configure the appropriate `A2A_*_URL` values for live delegation.

The LangGraph workflow is in `services/support_graph.py`: `triage → retrieve_knowledge → consult every matching specialist → compose final answer`. For a multi-domain request, such as a late order with a duplicate charge, Billing and Order specialists are contacted before the final answer is generated. Configure an `A2A_*_URL` for an external specialist; otherwise the app uses a scoped built-in OpenAI specialist. Without an API key, it remains usable in offline simulation mode.

The bundled sample knowledge base includes 20 realistic articles across Orders, Returns, Billing, Account, Technical, Privacy, and Support. To populate a new Pinecone index from these articles:

```bash
python ingest.py
```

## Validate

```bash
pytest -q
```
