"""
Based on recommendation to be able to run in
machine such as Macbook Air M3
or qwen3.5:9b if smaller model is needed
test also this model: llama3.1:8b
"""
MODEL = "mistral-small"
OLLAMA_OPTIONS = {"num_ctx": 8192}  # Ollama defaults to 4096 and silently truncates from the top

# Demo-only cloud fallback (LLM_PROVIDER=anthropic) — see llm.py. Not the default path.
CLOUD_MODEL = "claude-haiku-4-5"