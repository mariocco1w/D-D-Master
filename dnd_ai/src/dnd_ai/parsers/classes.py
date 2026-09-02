"""Parser de las clases del SRD 5.2.1 -> JSON.

Usa los tamaños de fuente: nombre de clase 18.0, cabeceras de sección 14.0,
rasgos/encabezados "Nivel N:" 12.0, cuerpo 10.0.
"""
from __future__ import annotations

import json
import re

from ..config import JSON_DIR, RAW_DIR
from .common import slugify, write_json

CLASS_SIZE = 18.0
SECTION_SIZE = 14.0
FEATURE_SIZE = 12.0
CAPTION_SIZE = 10.5  # "Atributos básicos de X", "Rasgos de X", "Lista de conjuros de X"

METADATA_LABELS = [
    "Característica principal",
    "Dado de puntos de golpe",
    "Competencias en tiradas de salvación",
    "Competencias en habilidades",
    "Competencias con armas",
    "Competencias con herramientas",
    "Entrenamiento con armaduras",
    "Equipo inicial",
]


def _load_lines() -> list[dict]:
    lines = json.loads((RAW_DIR / "clases.json").read_text(encoding="utf-8"))
    return _merge_split_headings(lines)


def _merge_split_headings(lines: list[dict]) -> list[dict]:
    """Une líneas de encabezado partidas por el salto de columna (mismo tamaño)."""
    out: list[dict] = []
    for line in lines:
        if out and line["size"] >= 11.5 and line["size"] == out[-1]["size"]:
            prev = out[-1]
            if not prev["text"].endswith((".")) or prev["text"].endswith(":"):
                prev = dict(prev, text=prev["text"] + " " + line["text"])
                out[-1] = prev
                continue
        out.append(line)
    return out


def _clean_meta_value(value: str) -> str:
    value = value.strip()
    return re.sub(r"\s+", " ", value)


def _parse_metadata(section_text: str) -> dict:
    """Extrae pares etiqueta/valor del bloque 'Atributos básicos de X'."""
    meta: dict = {}
    text = _clean_meta_value(section_text)
    matches = [i for i, lab in enumerate(METADATA_LABELS) if lab in text]
    if not matches:
        return meta
    positions = []
    for lab in METADATA_LABELS:
        idx = text.find(lab)
        if idx != -1:
            positions.append((idx, lab))
    positions.sort()
    for i, (idx, lab) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        value = text[idx + len(lab):end]
        meta[lab] = _clean_meta_value(value)
    return meta


def parse_classes(lines: list[dict] | None = None) -> list[dict]:
    if lines is None:
        lines = _load_lines()

    classes: list[dict] = []
    current_cls: dict | None = None
    current_sec: dict | None = None
    meta_buf: list[str] = []

    def flush_sec() -> None:
        nonlocal current_sec, meta_buf
        if current_sec is None:
            meta_buf = []
            return
        content = "\n".join(current_sec["_lines"]).strip()
        if current_sec["tipo"] == "atributos":
            current_sec["metadatos"] = _parse_metadata(content)
            current_sec.pop("_lines", None)
            current_sec.pop("contenido", None)
        else:
            current_sec["contenido"] = content
            current_sec.pop("_lines", None)
        current_cls["secciones"].append(current_sec)
        current_sec = None
        meta_buf = []

    def flush_cls() -> None:
        nonlocal current_cls
        if current_cls is not None:
            flush_sec()
            classes.append(current_cls)
        current_cls = None

    for line in lines:
        text = line["text"]
        size = line["size"]

        if size >= CLASS_SIZE and not (size >= 26.0 and text == "Clases"):
            flush_cls()
            current_cls = {
                "clase": text,
                "id": f"clases-{slugify(text)}",
                "secciones": [],
            }
            current_sec = {"titulo": "atributos-basicos", "tipo": "atributos", "_lines": []}
            continue

        if current_cls is None:
            continue

        if size >= SECTION_SIZE:
            flush_sec()
            tipo = "subclase" if re.match(r"^Subclase de", text) else "seccion"
            current_sec = {"titulo": text, "tipo": tipo, "_lines": []}
            continue

        if size >= FEATURE_SIZE:
            flush_sec()
            tipo = "rasgo" if re.match(r"^Nivel\s*\d+:", text) else "encabezado"
            current_sec = {"titulo": text, "tipo": tipo, "_lines": []}
            continue

        if current_sec is not None:
            current_sec["_lines"].append(text)
    flush_cls()
    return classes


def build() -> list[dict]:
    classes = parse_classes()
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    write_json(JSON_DIR / "clases.json", classes)
    return classes


if __name__ == "__main__":
    items = build()
    print(f"clases: {len(items)}")
    for c in items:
        metas = [s["metadatos"].get("Dado de puntos de golpe", "") for s in c["secciones"] if s["tipo"] == "atributos"]
        print(f" - {c['clase']}: {len(c['secciones'])} secciones, dHP={metas[0] if metas else '?'}")
