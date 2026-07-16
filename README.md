# care_chat

Local chatbot for care-product repair support (wheelchairs, support beds, and similar equipment). Describe what's wrong and the bot walks you through it:

- **Minor damage** (flat tire, torn upholstery, unresponsive remote, small mattress tear) — bot gives DIY repair steps from a built-in protocol catalog.
- **Major damage** (cracked frame, brake failure, motor failure, bent frame) — bot explains a temporary replacement will be arranged, collects your contact/pickup details conversationally, confirms with you, then logs a repair ticket.
- **Unclear input** — bot asks one clarifying question at a time instead of guessing.
- **Not in the catalog** — bot says so and offers to log a ticket anyway, rather than inventing repair advice.

Runs entirely local: FastAPI backend + [Ollama](https://ollama.com) for the model, plain HTML/JS frontend. No cloud calls, no accounts.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running

## Setup

```bash
ollama pull qwen2.5:14b-instruct

python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/uvicorn app:app --reload
```

Open **http://localhost:8000** and start chatting.

## Test

```bash
.venv/bin/pytest test_chat.py
```

No running model needed — `ollama.chat` is mocked.

## How it works

1. You describe a problem in the chat box.
2. The model matches it against `protocols.json` (a catalog of `product → issue → severity + repair steps`).
3. Minor issues get step-by-step DIY instructions back in chat.
4. Major issues trigger a conversational intake (name, contact, pickup address), then the bot logs a ticket to `tickets.jsonl` and gives you a ticket ID.

Chat history lives in memory per browser tab (`X-Session-Id`, stored in `localStorage`) and resets if the server restarts. Tickets are the only thing that persist, in `tickets.jsonl` — not committed to git, since it holds contact details.

## Extending the catalog

Add products/issues to `protocols.json`:

```json
{
  "wheelchair": {
    "flat tire": {
      "severity": "minor",
      "steps": ["...", "..."]
    }
  }
}
```

Keys are matched lowercase. No code changes needed — the bot picks up new entries on restart.

## Layout

See [`CLAUDE.md`](./CLAUDE.md) for architecture details and design decisions.
