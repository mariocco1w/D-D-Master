"""Parser de las reglas de juego (Cómo jugar, SRD 5.2.1) -> JSON.

Organiza el texto en capítulos (fuente 18.0) y secciones (fuente 14.0).
"""
from __future__ import annotations

import json
import re

from ..config import JSON_DIR, RAW_DIR
from .common import slugify, write_json

CHAPTER_SIZE = 18.0
SECTION_SIZE = 14.0


def _load_lines() -> list[dict]:
    lines = json.loads((RAW_DIR / "reglas.json").read_text(encoding="utf-8"))
    return _merge_split_headings(lines)


def _merge_split_headings(lines: list[dict]) -> list[dict]:
    """Une líneas de encabezado partidas por salto de línea/columna."""
    out: list[dict] = []
    for line in lines:
        if out and line["size"] >= 14.0 and line["size"] == out[-1]["size"]:
            prev = out[-1]
            if not prev["text"].endswith(".") or prev["text"].endswith(":"):
                prev = dict(prev, text=prev["text"] + " " + line["text"])
                out[-1] = prev
                continue
        out.append(line)
    return out


def parse_rules(lines: list[dict] | None = None) -> list[dict]:
    if lines is None:
        lines = _load_lines()

    rules: list[dict] = []
    current_chap: str = "Introducción"
    current_sec: dict | None = None

    def flush() -> None:
        nonlocal current_sec
        if current_sec is not None:
            text = "\n".join(current_sec["_lines"]).strip()
            if text:
                current_sec["contenido"] = text
                current_sec.pop("_lines", None)
                rules.append(current_sec)
        current_sec = None

    for line in lines:
        text = line["text"]
        size = line["size"]
        page = line["page"]

        if size >= 26.0 and text == "Cómo jugar":
            continue

        if size >= CHAPTER_SIZE:
            flush()
            current_chap = text
            current_sec = {
                "id": f"reglas-{slugify(current_chap)}",
                "capitulo": current_chap,
                "seccion": current_chap,
                "pagina": page,
                "_lines": [],
            }
            continue

        if size >= SECTION_SIZE:
            flush()
            sec_slug = slugify(text)
            chap_slug = slugify(current_chap)
            current_sec = {
                "id": f"reglas-{chap_slug}-{sec_slug}",
                "capitulo": current_chap,
                "seccion": text,
                "pagina": page,
                "_lines": [],
            }
            continue

        if current_sec is not None:
            current_sec["_lines"].append(text)

    flush()
    return rules


def build() -> list[dict]:
    rules = parse_rules()
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    write_json(JSON_DIR / "reglas.json", rules)
    return rules


if __name__ == "__main__":
    items = build()
    print(f"reglas: {len(items)} secciones")
    for r in items:
        print(f" - [{r['capitulo']}] {r['seccion']} (p.{r['pagina']}, {len(r['contenido'])} chars)")
