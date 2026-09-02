"""Utilidades comunes para los parsers del SRD."""
from __future__ import annotations

import re
from typing import Any

ACCENTS = str.maketrans(
    "áéíóúüñÁÉÍÓÚÜÑ", "aeiouunAEIOUUN"
)


def unaccent(text: str) -> str:
    return text.translate(ACCENTS)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", unaccent(text).lower()).strip("-")


def chunk_text(
    text: str, size: int = 900, overlap: int = 120
) -> list[str]:
    """Divide texto en trozos superpuestos sin cortar párrafos."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buflen = 0
    for p in paras:
        if buflen + len(p) > size and buf:
            chunks.append("\n\n".join(buf))
            carry = buf
            buf = []
            while carry and len("\n\n".join(buf)) < overlap:
                buf.insert(0, carry.pop())
            buflen = sum(len(x) for x in buf) + 2 * len(buf)
        buf.append(p)
        buflen += len(p) + 2
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def write_json(path: Any, data: Any) -> None:
    import json

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
