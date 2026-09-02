"""Extrae el texto del PDF del SRD 5.2.1 por secciones conservando el tamaño
de fuente por línea (para detectar títulos de forma robusta)."""
from __future__ import annotations

import json
import re

import pymupdf

from .config import PDF_PATH, RAW_DIR, SECTIONS, ensure_dirs

RUNNING_HEADER = "Documento de referencia del sistema 5.2.1"


def _clean_hyphenation_line(line: str) -> str:
    return line.replace("\u00ad", "").replace("\u2010", "-").replace("\u2011", "-")


def extract_section_lines(doc: pymupdf.Document, section: str) -> list[dict]:
    """Devuelve las líneas de una sección con su tamaño de fuente."""
    cfg = SECTIONS[section]
    start = cfg["first_page"]
    end = cfg["last_page"]
    first_text = doc[start].get_text("text")
    if cfg["start_heading"] not in first_text:
        raise ValueError(
            f"La sección '{section}' no empieza en la página {start}: "
            f"cabecera '{cfg['start_heading']}' no encontrada"
        )

    out: list[dict] = []
    for pi in range(start, end):
        page = doc[pi]
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = line["spans"]
                text = "".join(s["text"] for s in spans).strip()
                if not text:
                    continue
                text = _clean_hyphenation_line(text)
                if text == RUNNING_HEADER:
                    continue
                if re.fullmatch(r"\d{1,3}", text):
                    continue
                out.append(
                    {
                        "text": text,
                        "size": round(max(s["size"] for s in spans), 1),
                        "page": pi + 1,
                    }
                )
    return out


def _rejoin_hyphens(lines: list[dict]) -> list[dict]:
    """Une palabras partidas por guion al final de línea (guion blando/U+2011)."""
    result: list[dict] = []
    for i, line in enumerate(lines):
        text = line["text"]
        if re.search(r"-\s*$", text) and i + 1 < len(lines):
            nxt = lines[i + 1]["text"]
            if nxt and nxt[0].islower():
                merged = text[:-1].rstrip() + nxt.lstrip()
                line = dict(line, text=merged)
                lines[i + 1] = dict(lines[i + 1], text="")
                result.append(line)
                continue
        if text:
            result.append(line)
    return result


def extract_all() -> dict[str, list[dict]]:
    ensure_dirs()
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"No se encuentra el PDF: {PDF_PATH}")
    doc = pymupdf.open(PDF_PATH)
    result: dict[str, list[dict]] = {}
    for section in SECTIONS:
        lines = _rejoin_hyphens(extract_section_lines(doc, section))
        (RAW_DIR / f"{section}.json").write_text(
            json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        plain = "\n".join(l["text"] for l in lines if l["text"])
        (RAW_DIR / f"{section}.txt").write_text(plain, encoding="utf-8")
        result[section] = lines
        print(f"[extractor] {section}: {len(lines)} líneas ({len(plain)} chars)")
    doc.close()
    return result


if __name__ == "__main__":
    extract_all()
