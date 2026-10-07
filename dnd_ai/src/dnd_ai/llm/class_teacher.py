"""Preguntas sobre clases, respondidas solo con el catálogo del SRD."""
from __future__ import annotations

import sys

from ..classes.catalog import ClassCatalog, load_catalog
from ..classes.primer import render_ollama_brief
from ..config import OLLAMA_BASE_URL, OLLAMA_MODEL
from .ollama_client import OllamaUnavailable, chat, ollama_available

SYSTEM_ROLE = """Eres el archivero de clases de D&D Master.
Respondes en español y solo con el catálogo del SRD 5.2.1 que viene en este mensaje.
Cuando compares clases, usa la característica principal, el dado de puntos de golpe, las competencias y los rasgos que aparecen en el catálogo.
El SRD de este proyecto incluye una subclase de ejemplo por clase. No inventes otras subclases, conjuros ni cifras.
Si el catálogo no alcanza para responder, dilo con claridad."""


def build_messages(
    question: str,
    catalog: ClassCatalog | None = None,
) -> list[dict[str, str]]:
    catalog = catalog or load_catalog()
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("La pregunta está vacía")
    picked = catalog.mentioned_in(cleaned)
    if not picked:
        context = render_ollama_brief(catalog)
        scope = "Resumen corto de las doce clases."
    else:
        context = render_ollama_brief(catalog, picked)
        names = ", ".join(character_class.name for character_class in picked)
        scope = f"Resumen corto de: {names}."
    system = f"{SYSTEM_ROLE}\n\n{scope}\n\n{context}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": cleaned},
    ]


def answer_about_classes(
    question: str,
    catalog: ClassCatalog | None = None,
    *,
    model: str = OLLAMA_MODEL,
) -> str:
    return chat(build_messages(question, catalog), model=model)


def main() -> None:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print(
            'Uso: python -m dnd_ai.llm.class_teacher '
            '"¿En qué se diferencia un mago de un hechicero?"'
        )
        raise SystemExit(2)
    if not ollama_available():
        messages = build_messages(question)
        print(
            f"Ollama no responde en {OLLAMA_BASE_URL}. "
            f"El contexto de clases ya está armado ({len(messages[0]['content'])} caracteres) "
            f"para el modelo {OLLAMA_MODEL}."
        )
        print(
            "Instala Ollama y ejecuta `ollama pull "
            f"{OLLAMA_MODEL}`. En este equipo el banco de pruebas está en "
            "`python -m dnd_ai.llm.bench`."
        )
        raise SystemExit(1)
    try:
        print(answer_about_classes(question))
    except OllamaUnavailable as exc:
        print(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
