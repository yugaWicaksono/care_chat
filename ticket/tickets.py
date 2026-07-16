from pathlib import Path
import json
import uuid
from datetime import datetime, timezone

from prompt.prompts import PROTOCOLS

BASE = Path(__file__).parent.parent
TICKETS = BASE / "tickets.jsonl"

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "log_replacement_request",
        "description": (
            "Log a repair ticket: arranges a temporary replacement and pickup of the "
            "damaged item. Only call after the user has confirmed their details."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string", "description": "Product type, e.g. wheelchair"},
                "issue": {"type": "string", "description": "The issue, matching a catalog entry if possible"},
                "contact_name": {"type": "string", "description": "User's full name"},
                "contact_info": {"type": "string", "description": "Phone number or email"},
                "address": {"type": "string", "description": "Pickup/delivery address"},
                "notes": {"type": "string", "description": "Item id, serial number or extra notes"},
                "client_number": {
                    "type": "string",
                    "description": (
                        "If known from a prior lookup_customer call, include it — lets you "
                        "skip re-collecting contact/address."
                    ),
                },
            },
            "required": ["product", "issue", "contact_name", "contact_info", "address"],
        },
    },
}

TICKET_FIELDS = ("product", "issue", "contact_name", "contact_info", "address", "notes", "client_number")

def lookup_severity(product: str, issue: str) -> str:
    """
    Lookup severity based on product and issue
    :param product: the product from the catalog
    :param issue: issue with the product
    """
    # catalog is the source of truth for severity, never the model
    return PROTOCOLS.get(product.lower(), {}).get(issue.lower(), {}).get("severity", "unknown")


def fabricated_fields(args: dict, history: list) -> list[str]:
    """
    Method to prevent ticket being created when the user data is not complete
    :param args: the chat data containing response from the user
    :param history: the history of the user chat
    :return:
    """
    # while a miss would file a ticket with invented contact details
    user_text = " ".join(
        m["content"] for m in history if m.get("role") == "user" and m.get("content")
    ).casefold()
    return [
        field for field in ("contact_name", "contact_info", "address")
        if not str(args.get(field, "")).strip() or str(args[field]).casefold() not in user_text
    ]

def log_replacement_request(args: dict) -> dict:
    """
    Method to log a repair request
    :param args: output from the model based on the user chat
    :return:
    """
    ticket = {field: str(args.get(field, "")) for field in TICKET_FIELDS}
    ticket["ticket_id"] = str(uuid.uuid4())
    ticket["created_at"] = datetime.now(timezone.utc).isoformat()
    ticket["severity"] = lookup_severity(ticket["product"], ticket["issue"])
    with TICKETS.open("a") as f:
        f.write(json.dumps(ticket) + "\n")
    return {"ticket_id": ticket["ticket_id"], "status": "replacement arranged, pickup scheduled"}
