import psycopg
from psycopg.rows import dict_row

from customer.db import DATABASE_URL

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "lookup_customer",
        "description": (
            "Look up an existing customer by name or client number, to reuse their "
            "known contact details instead of asking again. Call this as soon as you "
            "know either their name or client number — early in the conversation, or "
            "right before filing a ticket, whichever comes first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Customer's name, if known"},
                "client_number": {"type": "string", "description": "Customer's client number, if known"},
            },
        },
    },
}


def find_customer(name: str | None = None, client_number: str | None = None) -> list[dict]:
    # ponytail: fresh connection per lookup, no pool — occasional single-user queries, add
    # psycopg_pool only if concurrency ever actually shows up as a bottleneck
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            if client_number:
                cur.execute(
                    "SELECT client_number, name, contact_info, address FROM customers "
                    "WHERE lower(client_number) = lower(%s)",
                    (client_number,),
                )
            elif name:
                cur.execute(
                    "SELECT client_number, name, contact_info, address FROM customers "
                    "WHERE name ILIKE %s",
                    (f"%{name}%",),
                )
            else:
                return []
            return cur.fetchall()


def lookup_customer(args: dict) -> dict:
    matches = find_customer(name=args.get("name"), client_number=args.get("client_number"))
    if len(matches) == 1:
        return {"match": "single", "customer": matches[0]}
    if len(matches) > 1:
        return {
            "match": "multiple",
            "candidates": [{"client_number": m["client_number"], "name": m["name"]} for m in matches],
        }
    return {"match": "none"}
