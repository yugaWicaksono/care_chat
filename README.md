# care_chat

Local chatbot for care-product repair support (wheelchairs, support beds, and similar equipment). Describe what's wrong and the bot walks you through it:

- **Minor damage** (flat tire, torn upholstery, unresponsive remote, small mattress tear) — bot gives DIY repair steps from a built-in protocol catalog.
- **Major damage** (cracked frame, brake failure, motor failure, bent frame) — bot explains a temporary replacement will be arranged, collects your contact/pickup details conversationally, confirms with you, then logs a repair ticket.
- **Returning customer** — if the bot recognizes you by name or client number, it reuses your contact details on file (with a quick confirmation) instead of asking you to retype everything.
- **Unclear input** — bot asks one clarifying question at a time instead of guessing.
- **Not in the catalog** — bot says so and offers to log a ticket anyway, rather than inventing repair advice.

Runs local: FastAPI backend + [Ollama](https://ollama.com) for the model, Postgres for customers and tickets, plain HTML/JS frontend. No cloud LLM, no accounts.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Docker (for the local Postgres database)

## Setup

```bash
cp .env.example .env          # set ADMIN_PASSWORD; Postgres defaults work as-is
docker compose up -d          # starts Postgres, loads customer + ticket schemas + example customers
ollama pull mistral-small

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

No running model or Postgres needed — `ollama.chat`, the customer lookup, and the ticket insert are all mocked.

## How it works

1. You describe a problem in the chat box.
2. The model matches it against `prompt/protocols.json` (a catalog of `product → issue → severity + repair steps`).
3. Minor issues get step-by-step DIY instructions back in chat.
4. Major issues trigger a customer lookup by name or client number (if not already resolved earlier in the conversation) against Postgres. Found → reuses the details on file after a quick confirmation. Not found → normal conversational intake (name, contact, pickup address). Either way, the bot logs a ticket to the `tickets` table in Postgres and gives you a ticket ID.

Chat history lives in memory per browser tab (`X-Session-Id`, stored in `localStorage`) and resets if the server restarts. Tickets and customers are the durable data, both in Postgres.

## Managing customers

The bot only *reads* the customer table — add real customers yourself:

```bash
docker compose exec db psql -U care_chat -c \
  "INSERT INTO customers (client_number, name, contact_info, address) VALUES ('1001', 'A. Voorbeeld', 'a@example.com', 'Straat 1, Stad');"
```

`customer/schema.sql` has the table definition; `customer/seed.sql` has a few example rows loaded automatically the first time the `db` container starts. Connection settings (including `DATABASE_URL`) live in `.env` — not committed, see `.env.example` for the template.

## Viewing tickets

Open **http://localhost:8000/admin/tickets** — a simple list + detail page, protected by HTTP Basic auth using the `ADMIN_USER`/`ADMIN_PASSWORD` you set in `.env`. This is the one part of the app with any auth, since it shows every customer's contact info in one place.

Or query directly:

```bash
docker compose exec db psql -U care_chat -c "SELECT * FROM tickets ORDER BY created_at DESC;"
```

`ticket/schema.sql` has the table definition.

## Extending the catalog

Add products/issues to `prompt/protocols.json`:

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
