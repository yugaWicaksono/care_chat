"""
Based on recommendation to be able to run in
machine such as Macbook Air M3
or qwen3.5:9b if smaller model is needed
"""
# MODEL = "mistral-small" 
MODEL = "qwen3.5:9b"
OLLAMA_OPTIONS = {"num_ctx": 8192}  # Ollama defaults to 4096 and silently truncates from the top