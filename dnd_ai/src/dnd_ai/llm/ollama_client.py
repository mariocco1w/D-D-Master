"""Cliente mínimo del API local de Ollama."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_NUM_CTX

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class OllamaUnavailable(RuntimeError):
    """Ollama no respondió o devolvió una respuesta vacía."""


def ollama_available(base_url: str = OLLAMA_BASE_URL, timeout: float = 2.0) -> bool:
    return list_models(base_url=base_url, timeout=timeout) is not None


def list_models(base_url: str = OLLAMA_BASE_URL, timeout: float = 2.0) -> list[str] | None:
    request = urllib.request.Request(base_url.rstrip("/") + "/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    models = body.get("models") if isinstance(body, dict) else None
    if not isinstance(models, list):
        return []
    names: list[str] = []
    for item in models:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return names


def model_is_installed(installed: list[str], model: str) -> bool:
    wanted = model.removesuffix(":latest")
    for name in installed:
        if name == model or name.removesuffix(":latest") == wanted:
            return True
    return False


def chat(
    messages: list[dict[str, str]],
    *,
    model: str = OLLAMA_MODEL,
    base_url: str = OLLAMA_BASE_URL,
    timeout: float = 180.0,
    num_ctx: int = OLLAMA_NUM_CTX,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": num_ctx, "temperature": 0.2},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise OllamaUnavailable(
            f"Ollama rechazó la consulta al modelo {model}. {detail}".strip()
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise OllamaUnavailable(
            f"No se pudo consultar a Ollama en {base_url} con el modelo {model}."
        ) from exc

    message = body.get("message") if isinstance(body, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise OllamaUnavailable(f"Ollama respondió sin texto para el modelo {model}.")
    return _THINK_BLOCK.sub("", content).strip()
