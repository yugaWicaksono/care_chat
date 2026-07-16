# care_chat

Local chatbot for care-product repair support (wheelchairs, support beds). Users describe damage; the bot matches it against a repair-protocol catalog, walks them through DIY fixes for minor issues, and for major damage arranges a temporary replacement + logs a pickup/repair ticket. It can also recognize a returning customer (by name or client number, looked up against Postgres) and reuse their contact details instead of re-asking. Runs local: FastAPI + Ollama for the model, Postgres for customer lookups, no cloud LLM.

## Architecture

- `app.py` — FastAPI app, routes, session store, tool-call dispatch loop. No longer owns the system prompt, tool schemas, or ticket/customer logic.
- `prompt/` — `const.py` (MODEL, OLLAMA_OPTIONS), `prompts.py` (loads `prompt/protocols.json`, builds SYSTEM_PROMPT), `protocols.json` (catalog: `product -> issue -> {severity: minor|major, steps: [...]}`, lowercase keys — extend here to support new products, no code change needed), `__init__.py` re-exports `SYSTEM_PROMPT`, `MODEL`, `OLLAMA_OPTIONS`.
- `ticket/` — `tickets.py` (TOOL_SCHEMA, TICKET_FIELDS, lookup_severity, fabricated_fields, log_replacement_request, TICKETS path; imports PROTOCOLS from `prompt.prompts` rather than reloading it), `__init__.py` re-exports `TOOL_SCHEMA`, `fabricated_fields`, `log_replacement_request`.
- `customer/` — `db.py` (`DATABASE_URL`, env-overridable), `customers.py` (TOOL_SCHEMA for `lookup_customer`, `find_customer` raw query, `lookup_customer` dispatch wrapper), `schema.sql`/`seed.sql` (auto-run by the `db` docker-compose service on first start), `__init__.py` re-exports `TOOL_SCHEMA`, `lookup_customer`. **Lookup-only** — the bot never writes to this table, only the operator does (via `psql`/SQL insert).
- `static/index.html` — chat UI, plain HTML/CSS/JS, no build step.
- `tickets.jsonl` — append-only ticket log, created at runtime. Contains user PII; gitignored. One JSON object per line. Now also carries `client_number` when the ticket was filed for a looked-up customer.
- `docker-compose.yml` — local Postgres for the customer table, schema + example rows auto-loaded on first `docker compose up`.
- `test_chat.py` — smoke tests with mocked `ollama.chat` and mocked `customer.customers.find_customer`; no model, no Ollama, no Postgres needed to run.

Model: `mistral-small` (constant `MODEL` in `prompt/const.py`, ~14GB). Switched from `qwen2.5:14b-instruct` — same/better Dutch fluency, and noticeably more reliable structured tool-calling: qwen2.5:14b occasionally skipped `lookup_customer` while claiming it had looked someone up, or leaked a hand-written pseudo tool-call as visible text instead of a real tool call; 5/5 trials on mistral-small produced a clean structured call. One-line swap in `prompt/const.py` to try something else later.

## Key design decisions (don't undo casually)

- **Catalog stuffed into system prompt, no RAG.** Catalog is small; keep it that way until it isn't.
- **`num_ctx: 8192` in every `ollama.chat` call.** Ollama defaults to 4096 and silently truncates from the top — the model forgets the catalog. Don't remove.
- **Severity resolved server-side** (`lookup_severity`, in `ticket/tickets.py`) from protocols.json at tool execution. Never trust severity from the model.
- **Fabrication guard** (`fabricated_fields`, in `ticket/tickets.py`): tool call rejected unless contact_name/contact_info/address appear literally (casefolded substring) in the user's own messages this session. Smaller models otherwise invent "John Doe" contact details and files fake tickets. False reject just makes the bot re-ask — that direction is fine.
- **Sessions in-memory**, keyed by `X-Session-Id` header (browser localStorage UUID). Now `{"history": [...], "verified_customers": {}}` instead of a bare list. Lost on restart; only tickets are durable. Swap for sqlite/postgres-backed sessions only if continuity is actually needed.
- **Customer records never trusted from the model.** A `lookup_customer` tool call that returns exactly one match gets cached into the session's `verified_customers` dict. Only when `log_replacement_request` is called with a `client_number` that's actually in that dict does the server override `contact_name`/`contact_info`/`address` with the DB record — the model's own values for those fields are discarded. Without a verified match, the existing `fabricated_fields` guard still applies. This closes the obvious bypass: claiming a `client_number` plus plausible-looking contact fields doesn't work unless a real lookup happened first.

## Commands

```bash
cp .env.example .env                # Postgres credentials + DATABASE_URL, gitignored
docker compose up -d                # local Postgres for customer lookups, schema+seed auto-loaded
ollama pull mistral-small   # once, ~14GB
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest test_chat.py     # fast, no model/Postgres needed
.venv/bin/uvicorn app:app --reload  # http://localhost:8000
```

Credentials live only in `.env` (gitignored) — `docker-compose.yml` reads `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` from it automatically, and `customer/db.py` loads `DATABASE_URL` from it via `python-dotenv`. No credentials are hardcoded in source; `customer/db.py` raises at import time if `DATABASE_URL` isn't set.

## Rules

- Never put real user PII (emails, names, addresses) in tests or test payloads — synthetic data only (`example.com`, fake names).
- System prompt says: never invent repair steps for uncatalogued products — this is safety-relevant (care equipment). Keep that instruction when editing the prompt.
- Keep it small: no auth, no framework on the frontend, no ORM/connection pool/migrations framework for the customer table unless requirements change.
- The `customers` table is lookup-only from the app's side — never add a write/insert path from the chat flow. New customers go in via SQL directly.
