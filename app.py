import json
import os
import secrets

import ollama
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from pathlib import Path

from prompt import SYSTEM_PROMPT, MODEL, OLLAMA_OPTIONS
from ticket import (
    TOOL_SCHEMA as TICKET_TOOL_SCHEMA,
    fabricated_fields,
    create_replacement_request,
    list_tickets,
    get_ticket,
)
from customer import TOOL_SCHEMA as CUSTOMER_TOOL_SCHEMA, lookup_customer
from product import TOOL_SCHEMA as PRODUCT_TOOL_SCHEMA, find_suitable_wheelchairs, PRODUCT_SYSTEM_PROMPT

load_dotenv()

BASE = Path(__file__).parent

app = FastAPI()
#in-memory session store, lost on restart; swap for sqlite if continuity needed
sessions: dict[str, dict] = {}
# separate store for the product-advice chat — genuinely separate conversations, no shared state
product_sessions: dict[str, list] = {}

security = HTTPBasic()
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    if not ADMIN_PASSWORD:
        raise HTTPException(500, "ADMIN_PASSWORD not set — add it to .env")
    valid = secrets.compare_digest(credentials.username, ADMIN_USER) and secrets.compare_digest(
        credentials.password, ADMIN_PASSWORD
    )
    if not valid:
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})


class ChatIn(BaseModel):
    message: str


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/product-advies")
def product_advice_page():
    return FileResponse(BASE / "static" / "product.html")


@app.get("/admin/tickets")
def admin_tickets_page(_: None = Depends(require_admin)):
    return FileResponse(BASE / "static" / "tickets.html")


@app.get("/api/tickets")
def api_tickets_list(_: None = Depends(require_admin)):
    return list_tickets()


@app.get("/api/tickets/{ticket_id}")
def api_ticket_detail(ticket_id: str, _: None = Depends(require_admin)):
    ticket = get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(404, "ticket not found")
    return ticket


@app.post("/chat")
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


@app.post("/chat/product")
def chat_product(body: ChatIn, x_session_id: str = Header(...)):
    history = product_sessions.setdefault(
        x_session_id, [{"role": "system", "content": PRODUCT_SYSTEM_PROMPT}]
    )
    history.append({"role": "user", "content": body.message})

    response = ollama.chat(
        model=MODEL, messages=history, tools=[PRODUCT_TOOL_SCHEMA], options=OLLAMA_OPTIONS
    )
    message = response["message"]
    history.append(message)

    if message.get("tool_calls"):
        for call in message["tool_calls"]:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            if name == "find_suitable_wheelchairs":
                result = find_suitable_wheelchairs(args)
            else:
                result = {"error": f"unknown tool: {name}"}
            history.append({"role": "tool", "content": json.dumps(result)})
        response = ollama.chat(model=MODEL, messages=history, options=OLLAMA_OPTIONS)
        message = response["message"]
        history.append(message)

    return {"reply": message["content"]}
