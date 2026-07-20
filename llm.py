import json
import os
import ollama
from dotenv import load_dotenv

from const import CLOUD_MODEL, MODEL, OLLAMA_OPTIONS

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")

def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    if LLM_PROVIDER == "cloud":
        return _chat_anthropic(messages, tools)
    return _chat_ollama(messages, tools)


def _chat_ollama(messages: list[dict], tools: list[dict] | None):
    return ollama.chat(model=MODEL, messages=messages, tools=tools, options=OLLAMA_OPTIONS)


def _tool_schema_to_anthropic(tool: dict) -> dict:
    fn = tool["function"]
    return {"name": fn["name"], "description": fn["description"], "input_schema": fn["parameters"]}


def _to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    system = ""
    out = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        role = msg["role"] if isinstance(msg, dict) else msg.get("role")
        content = msg["content"] if isinstance(msg, dict) else msg.get("content")
        tool_calls = msg.get("tool_calls") if isinstance(msg, dict) else msg.get("tool_calls")

        if role == "system":
            system = content
        elif role == "assistant" and tool_calls:
            blocks = []
            if content:
                blocks.append({"type": "text", "text": content})
            ids = []
            for idx, call in enumerate(tool_calls):
                tool_id = f"toolu_{i}_{idx}"
                ids.append(tool_id)
                args = call["function"]["arguments"]
                if isinstance(args, str):
                    args = json.loads(args)
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tool_id,
                        "name": call["function"]["name"],
                        "input": args,
                    }
                )
            out.append({"role": "assistant", "content": blocks})

            # ollama-style history has one {"role": "tool", ...} entry per call, in order
            results = []
            for tool_id in ids:
                i += 1
                result_content = messages[i]["content"]
                results.append(
                    {"type": "tool_result", "tool_use_id": tool_id, "content": result_content}
                )
            out.append({"role": "user", "content": results})
        else:
            out.append({"role": role, "content": content})
        i += 1
    return system, out


def _chat_anthropic(messages: list[dict], tools: list[dict] | None):
    import anthropic

    client = anthropic.Anthropic()
    system, anthropic_messages = _to_anthropic_messages(messages)

    kwargs = {}
    if tools:
        kwargs["tools"] = [_tool_schema_to_anthropic(t) for t in tools]

    response = client.messages.create(
        model=CLOUD_MODEL,
        max_tokens=1024,
        system=system,
        messages=anthropic_messages,
        **kwargs,
    )

    text = "".join(b.text for b in response.content if b.type == "text")
    tool_calls = [
        {"function": {"name": b.name, "arguments": b.input}}
        for b in response.content
        if b.type == "tool_use"
    ]
    return {"message": {"role": "assistant", "content": text, "tool_calls": tool_calls or None}}
