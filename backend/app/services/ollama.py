import requests

from app.core.config import (
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
)


def generate_response(prompt: str) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=OLLAMA_TIMEOUT,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not communicate with Ollama: {exc}"
        ) from exc

    try:
        output = response.json()["response"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(
            "Ollama returned an unexpected response."
        ) from exc

    return output