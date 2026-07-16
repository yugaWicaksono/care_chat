from .db_actions import find_customer

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
