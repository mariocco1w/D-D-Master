"""Parser del glosario de reglas (SRD 5.2.1) -> entradas JSON.

Usa las líneas extraídas con su tamaño de fuente: los términos del glosario
tienen fuente 12.0 frente al cuerpo de 10.0.
"""
from __future__ import annotations

import json
import re

from ..config import JSON_DIR, RAW_DIR
from .common import slugify, write_json

TERM_MIN_SIZE = 11.5  # los términos usan fuente 12.0
INTRO_MAX_SIZE = 14.0  # las cabeceras de la introducción (18.0) no son términos

TAGS = {
    "acción": "accion",
    "estado": "estado",
    "peligro": "peligro",
    "área de efecto": "area_efecto",
    "actitud": "actitud",
}


def load_lines(section: str = "glosario") -> list[dict]:
    return json.loads((RAW_DIR / f"{section}.json").read_text(encoding="utf-8"))


def parse_glossary(lines: list[dict] | None = None) -> list[dict]:
    if lines is None:
        lines = load_lines()

    entries: list[dict] = []
    current: dict | None = None
    body: list[str] = []

    def flush() -> None:
        nonlocal current, body
        if current is not None:
            current["definicion"] = "\n".join(body).strip()
            entries.append(current)
        current = None
        body = []

    for line in lines:
        text = line["text"]
        size = line["size"]
        is_term = TERM_MIN_SIZE <= size <= INTRO_MAX_SIZE
        if is_term:
            tag = None
            m = re.match(r"^(.*?)\s*\[([^\]]+)\]$", text)
            if m:
                term, tag_raw = m.group(1).strip(), m.group(2).strip().lower()
                tag = TAGS.get(tag_raw)
            else:
                term = text
            flush()
            current = {
                "termino": term,
                "tag": tag,
                "id": f"glosario-{slugify(term)}",
            }
            continue
        if current is not None:
            body.append(text)
    flush()

    return entries


def build() -> list[dict]:
    entries = parse_glossary()
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    write_json(JSON_DIR / "glosario.json", entries)
    return entries


if __name__ == "__main__":
    items = build()
    print(f"glosario: {len(items)} entradas")
