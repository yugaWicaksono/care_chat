import json

import ollama
from fastapi import FastAPI, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel

from pathlib import Path

from prompt import SYSTEM_PROMPT, MODEL, OLLAMA_OPTIONS
from ticket import TOOL_SCHEMA, fabricated_fields, log_replacement_request

BASE = Path(__file__).parent

app = FastAPI()
#in-memory session store, lost on restart; swap for sqlite if continuity needed
sessions: dict[str, list] = {}


class ChatIn(BaseModel):
    message: str


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.post("/chat")
def chat(body: ChatIn, x_session_id: str = Header(...)):
    history = sessions.setdefault(x_session_id, [{"role": "system", "content": SYSTEM_PROMPT}])
    history.append({"role": "user", "content": body.message})

    response = ollama.chat(model=MODEL, messages=history, tools=[TOOL_SCHEMA], options=OLLAMA_OPTIONS)
    message = response["message"]
    history.append(message)

    if message.get("tool_calls"):
        for call in message["tool_calls"]:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            if name == "log_replacement_request":
                bad = fabricated_fields(args, history)
                if bad:
                    result = {
                        "error": f"Rejected: {', '.join(bad)} not provided by the user in this "
                        "conversation. Ask the user for their real details — never guess."
                    }
                else:
                    result = log_replacement_request(args)
            else:
                result = {"error": f"unknown tool: {name}"}
            history.append({"role": "tool", "content": json.dumps(result)})
        response = ollama.chat(model=MODEL, messages=history, options=OLLAMA_OPTIONS)
        message = response["message"]
        history.append(message)

    return {"reply": message["content"]}
