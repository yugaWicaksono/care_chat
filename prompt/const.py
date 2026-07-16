"""

This model is large enough to have
"""
MODEL = "qwen2.5:7b-instruct"
OLLAMA_OPTIONS = {"num_ctx": 8192}  # Ollama defaults to 4096 and silently truncates from the top