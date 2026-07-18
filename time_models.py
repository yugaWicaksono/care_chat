import time

import ollama

from const import OLLAMA_OPTIONS

MODELS = ["qwen3.5:9b", "mistral-small"]
PROMPT = "M'n rolstoel heeft een gescheurd frame, wat nu?"


def time_model(model: str) -> float:
    start = time.perf_counter()
    ollama.chat(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
        options=OLLAMA_OPTIONS,
    )
    return time.perf_counter() - start


if __name__ == "__main__":
    for model in MODELS:
        elapsed = time_model(model)
        print(f"{model}: {elapsed:.2f}s")
