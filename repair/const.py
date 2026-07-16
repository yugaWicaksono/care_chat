"""
Based on recommendation to be able to run in
machine such as Macbook Air M3
"""
MODEL = "mistral-small"
OLLAMA_OPTIONS = {"num_ctx": 8192}  # Ollama defaults to 4096 and silently truncates from the top