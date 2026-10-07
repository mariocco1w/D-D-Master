"""Limpieza ligera del texto extraído del PDF del SRD."""
from __future__ import annotations

import re


def normalize_srd_text(text: str) -> str:
    """Une saltos de columna y espacios duros sin reescribir las palabras."""
    cleaned = text.replace("\u00a0", " ").replace("\u00ad", "").replace("\u200b", "")
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]*\n[ \t]*", " ", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def without_progression_table(text: str, class_name: str) -> str:
    """Quita la tabla de progresión que el extractor pegó al primer rasgo."""
    cleaned = normalize_srd_text(text)
    marker = f"rasgos de {class_name}".lower()
    index = cleaned.lower().find(marker)
    if index > 40:
        return cleaned[:index].strip()
    return cleaned
