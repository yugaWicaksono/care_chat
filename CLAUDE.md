# care_chat

Local chatbot for care-product repair support (wheelchairs, support beds). Users describe damage; the bot matches it against a repair-protocol catalog, walks them through DIY fixes for minor issues, and for major damage arranges a temporary replacement + logs a pickup/repair ticket. Runs fully local: FastAPI + Ollama, no cloud.

## Architecture

- `app.py` — FastAPI app, routes, session store, tool-call dispatch loop. No longer owns the system prompt, tool schema, or ticket logic.
- `prompt/` — `const.py` (MODEL, OLLAMA_OPTIONS), `main.py` (loads `protocols.json`, builds SYSTEM_PROMPT), `__init__.py` re-exports `SYSTEM_PROMPT`, `MODEL`, `OLLAMA_OPTIONS`.
- `ticket/` — `main.py` (TOOL_SCHEMA, TICKET_FIELDS, lookup_severity, fabricated_fields, log_replacement_request, TICKETS path; imports PROTOCOLS from `prompt.main` rather than reloading it), `__init__.py` re-exports `TOOL_SCHEMA`, `fabricated_fields`, `log_replacement_request`.
- `protocols.json` — catalog: `product -> issue -> {severity: minor|major, steps: [...]}`. Lowercase keys; severity lookup depends on it. Extend here to support new products — no code change needed. Loaded once, by `prompt/main.py`; `ticket/main.py` imports it rather than reading the file itself.
- `static/index.html` — chat UI, plain HTML/CSS/JS, no build step.
- `tickets.jsonl` — append-only ticket log, created at runtime. Contains user PII; gitignored. One JSON object per line.
- `test_chat.py` — smoke tests with mocked `ollama.chat`; no model/Ollama needed to run.

Model: `qwen2.5:7b-instruct` (constant `MODEL` in `prompt/const.py`). Upgrade path: `qwen2.5:14b-instruct`, one-line swap.

## Key design decisions (don't undo casually)

- **Catalog stuffed into system prompt, no RAG.** Catalog is small; keep it that way until it isn't.
- **`num_ctx: 8192` in every `ollama.chat` call.** Ollama defaults to 4096 and silently truncates from the top — the model forgets the catalog. Don't remove.
- **Severity resolved server-side** (`lookup_severity`, in `ticket/main.py`) from protocols.json at tool execution. Never trust severity from the model.
- **Fabrication guard** (`fabricated_fields`, in `ticket/main.py`): tool call rejected unless contact_name/contact_info/address appear literally (casefolded substring) in the user's own messages this session. The 7b model otherwise invents "John Doe" contact details and files fake tickets. False reject just makes the bot re-ask — that direction is fine.
- **Sessions in-memory**, keyed by `X-Session-Id` header (browser localStorage UUID). Lost on restart; only tickets are durable. Swap for sqlite only if continuity is actually needed.

## Commands

```bash
ollama pull qwen2.5:7b-instruct   # once
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest test_chat.py     # fast, no model needed
.venv/bin/uvicorn app:app --reload  # http://localhost:8000
```

## Rules

- Never put real user PII (emails, names, addresses) in tests or test payloads — synthetic data only (`example.com`, fake names).
- System prompt says: never invent repair steps for uncatalogued products — this is safety-relevant (care equipment). Keep that instruction when editing the prompt.
- Keep it small: no auth, no DB, no framework on the frontend unless requirements change.
