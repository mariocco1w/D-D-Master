"""Fragmentos cortos de reglas y glosario para una pregunta."""
from __future__ import annotations

import json
import re

from ..config import JSON_DIR
from ..knowledge.parsers.common import unaccent

_TOKEN = re.compile(r"[a-z0-9]{4,}")
_RULES_ROLE = """Eres el archivero de reglas de D&D Master.
Respondes en español y solo con los fragmentos del SRD 5.2.1 que vienen en este mensaje.
Si los fragmentos no alcanzan, dilo. No inventes cifras ni condiciones."""


def build_rules_messages(question: str) -> list[dict[str, str]]:
    cleaned = question.strip()
    if not cleaned:
        raise ValueError("La pregunta está vacía")
    context = retrieve_rules(cleaned)
    return [
        {"role": "system", "content": f"{_RULES_ROLE}\n\n{context}"},
        {"role": "user", "content": cleaned},
    ]


def retrieve_rules(question: str, glossary_hits: int = 3, rule_hits: int = 2) -> str:
    glossary = _load_json("glosario.json")
    rules = _load_json("reglas.json")
    asked = _tokens(question)
    glossary_scored = sorted(
        ((_glossary_score(asked, item), item) for item in glossary if isinstance(item, dict)),
        key=lambda pair: pair[0],
        reverse=True,
    )
    rules_scored = sorted(
        (
            (
                _overlap(asked, f"{item.get('seccion', '')} {item.get('contenido', '')}"),
                item,
            )
            for item in rules
            if isinstance(item, dict)
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    lines = ["Fragmentos del SRD para esta pregunta."]
    wrote = False
    for score, item in glossary_scored[:glossary_hits]:
        if score <= 0:
            continue
        term = str(item.get("termino", "")).strip()
        definition = _clip(str(item.get("definicion", "")))
        lines.append(f"- Glosario, {term}: {definition}")
        wrote = True
    for score, item in rules_scored[:rule_hits]:
        if score <= 0:
            continue
        section = str(item.get("seccion", "")).strip()
        page = item.get("pagina", "")
        body = _clip(str(item.get("contenido", "")))
        lines.append(f"- Cómo jugar, {section} (p. {page}): {body}")
        wrote = True
    if not wrote:
        lines.append("No hay un fragmento que coincida con la pregunta.")
    return "\n".join(lines)


def _load_json(name: str) -> list[object]:
    path = JSON_DIR / name
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{name} no contiene una lista")
    return raw


def _tokens(text: str) -> set[str]:
    return set(_TOKEN.findall(unaccent(text).lower()))


def _glossary_score(asked: set[str], item: dict[str, object]) -> int:
    term = str(item.get("termino", ""))
    term_tokens = _tokens(term)
    shared = term_tokens & asked
    score = _overlap(asked, f"{term} {item.get('definicion', '')}") + (5 * len(shared))
    if term_tokens and term_tokens <= asked:
        score += 10
    return score


def _overlap(asked: set[str], text: str) -> int:
    return len(asked & _tokens(text))


def _clip(text: str, limit: int = 500) -> str:
    cleaned = " ".join(text.replace("\u00a0", " ").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "…"
