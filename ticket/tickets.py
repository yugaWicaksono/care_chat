from datetime import datetime, timezone

from repair.prompts import PROTOCOLS

from .db_actions import insert_ticket
from .util import generate_ticket_id

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_replacement_request",
        "description": (
            "Log a repair ticket: arranges a temporary replacement and pickup of the "
            "damaged item. Only call after the user has confirmed their details."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product": {"type": "string", "description": "Product type, e.g. wheelchair"},
                "product_model": {
                    "type": "string",
                    "description": (
                        "The specific catalog model name if the user named or confirmed one "
                        "(e.g. 'BariatricRest XL'). Leave empty if unknown — never guess."
                    ),
                },
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

TICKET_FIELDS = (
    "product", "product_model", "issue", "contact_name", "contact_info", "address", "notes",
    "client_number",
)

def lookup_severity(product: str, issue: str, product_model: str = "") -> str:
    """
    Lookup severity based on product and issue
    :param product: the product from the catalog
    :param issue: issue with the product
    :param product_model: specific catalog model, if known — checked first for a
        model-specific override before falling back to the generic product entry
    """
    # catalog is the source of truth for severity, never the model
    if product_model:
        model_entry = PROTOCOLS.get("models", {}).get(product_model.lower(), {}).get(issue.lower())
        if model_entry:
            return model_entry["severity"]
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

def create_replacement_request(args: dict) -> dict:
    """
    Method to create a repair request and save it in the database
    :param args: output from the model based on the user chat
    :return:
    """
    ticket = {field: str(args.get(field, "")) for field in TICKET_FIELDS}
    ticket["ticket_id"] = generate_ticket_id()
    ticket["created_at"] = datetime.now(timezone.utc)
    ticket["severity"] = lookup_severity(ticket["product"], ticket["issue"], ticket["product_model"])
    insert_ticket(ticket)
    return {"ticket_id": ticket["ticket_id"], "status": "replacement arranged, pickup scheduled"}
