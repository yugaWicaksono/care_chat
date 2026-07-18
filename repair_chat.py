import json
from pathlib import Path

import ollama
from fastapi import APIRouter, Header
from fastapi.responses import FileResponse

from chat_types import ChatIn
from const import MODEL, OLLAMA_OPTIONS
from customer import TOOL_SCHEMA as CUSTOMER_TOOL_SCHEMA
from customer import lookup_customer
from repair import SYSTEM_PROMPT
from ticket import (
    TOOL_SCHEMA as TICKET_TOOL_SCHEMA,
)
from ticket import (
    create_replacement_request,
    fabricated_fields,
)

BASE = Path(__file__).parent

router = APIRouter()
# in-memory session store, lost on restart; swap for sqlite if continuity needed
sessions: dict[str, dict] = {}


@router.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@router.post("/chat")
def chat(body: ChatIn, x_session_id: str = Header(...)):
    session = sessions.setdefault(
        x_session_id,
        {"history": [{"role": "system", "content": SYSTEM_PROMPT}], "verified_customers": {}},
    )
    history = session["history"]
    history.append({"role": "user", "content": body.message})

    tools = [TICKET_TOOL_SCHEMA, CUSTOMER_TOOL_SCHEMA]
    response = ollama.chat(model=MODEL, messages=history, tools=tools, options=OLLAMA_OPTIONS)
    message = response["message"]
    history.append(message)

    if message.get("tool_calls"):
        for call in message["tool_calls"]:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            if name == "create_replacement_request":
                verified = session["verified_customers"].get(args.get("client_number"))
                if verified:
                    # server-held customer record wins over whatever the model claims
                    args = {
                        **args,
                        "contact_name": verified["name"],
                        "contact_info": verified["contact_info"],
                        "address": verified["address"],
                        "client_number": verified["client_number"],
                    }
                    result = create_replacement_request(args)
                else:
                    bad = fabricated_fields(args, history)
                    if bad:
                        result = {
                            "error": f"Rejected: {', '.join(bad)} not provided by the user in this "
                            "conversation. Ask the user for their real details — never guess."
                        }
                    else:
                        result = create_replacement_request(args)
            elif name == "lookup_customer":
                result = lookup_customer(args)
                if result.get("match") == "single":
                    customer = result["customer"]
                    session["verified_customers"][customer["client_number"]] = customer
            else:
                result = {"error": f"unknown tool: {name}"}
            history.append({"role": "tool", "content": json.dumps(result)})
        response = ollama.chat(model=MODEL, messages=history, options=OLLAMA_OPTIONS)
        message = response["message"]
        history.append(message)

    return {"reply": message["content"]}
