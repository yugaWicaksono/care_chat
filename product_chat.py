import json
from pathlib import Path

import ollama
from fastapi import APIRouter, Header
from fastapi.responses import FileResponse

from chat_types import ChatIn
from product import PRODUCT_SYSTEM_PROMPT, find_suitable_wheelchairs
from product import TOOL_SCHEMA as PRODUCT_TOOL_SCHEMA
from prompt import MODEL, OLLAMA_OPTIONS

BASE = Path(__file__).parent

router = APIRouter()
# separate store from the repair chat — genuinely separate conversations, no shared state
product_sessions: dict[str, list] = {}


@router.get("/product-advies")
def product_advice_page():
    return FileResponse(BASE / "static" / "product.html")


@router.post("/chat/product")
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
