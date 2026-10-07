"""Texto de clases que se entrega al modelo."""
from __future__ import annotations

import re
from typing import assert_never

from ..config import CLASS_PRIMER_PATH
from .catalog import ClassCatalog, load_catalog
from .model import CharacterClass, ClassSection, SectionKind
from .text import normalize_srd_text, without_progression_table

DOSSIER_CHAR_BUDGET = 12_000
_LEVEL_ONE = re.compile(r"^Nivel\s*1:\s*(.+)$", re.IGNORECASE)


def render_primer(catalog: ClassCatalog) -> str:
    blocks = [
        "Catálogo de clases del SRD 5.2.1 (español).",
        "Hay doce clases. Cada una trae una sola subclase de ejemplo, la que publica el SRD.",
        "Este texto es la fuente para hablar de clases. No añadas clases ni subclases que no aparezcan aquí.",
        "",
    ]
    blocks.extend(render_summary(character_class) for character_class in catalog.all())
    return "\n\n".join(blocks).strip() + "\n"


def render_summary(character_class: CharacterClass) -> str:
    lines = [f"## {character_class.name}", f"Id: {character_class.class_id}"]
    for label, value in character_class.attributes().labeled():
        if value:
            lines.append(f"- {label}: {value}")
    lines.append("- Rasgos de clase:")
    for feature in character_class.class_features():
        lines.append(f"  - {_title(feature)}")
    headings = character_class.option_headings()
    if headings:
        lines.append("- Apartados:")
        for heading in headings:
            lines.append(f"  - {_title(heading)}")
    subclass = character_class.subclass()
    if subclass is not None:
        lines.append(f"- Subclase de ejemplo: {_title(subclass)}")
        for feature in character_class.subclass_features():
            lines.append(f"  - {_title(feature)}")
    return "\n".join(lines)


def render_ollama_brief(
    catalog: ClassCatalog,
    only: tuple[CharacterClass, ...] | None = None,
) -> str:
    """Resumen corto para un modelo local con poca memoria."""
    selected = only if only else catalog.all()
    lines = [
        "Clases del SRD 5.2.1.",
        "Responde solo con estas líneas. La subclase de ejemplo llega en el nivel 3, no hoy.",
    ]
    for character_class in selected:
        attributes = character_class.attributes()
        level_one: list[str] = []
        for feature in character_class.class_features():
            match = _LEVEL_ONE.match(normalize_srd_text(feature.title))
            if match:
                level_one.append(match.group(1).strip())
        subclass = character_class.subclass()
        subclass_name = (
            normalize_srd_text(subclass.title) if subclass is not None else "sin subclase de ejemplo"
        )
        traits = ", ".join(level_one) if level_one else "sin rasgos de nivel 1"
        lines.append(
            f"- {character_class.name}: característica {attributes.primary_ability}; "
            f"dado {attributes.hit_die}; salvaciones {attributes.saving_throws}; "
            f"nivel 1: {traits}; subclase de ejemplo: {subclass_name}."
        )
    return "\n".join(lines)


def render_dossier(character_class: CharacterClass) -> str:
    parts = [render_summary(character_class), "### Texto de referencia"]
    used = len(parts[0])
    for section in character_class.sections:
        limit = _body_limit(section.kind)
        if limit == 0:
            continue
        body = _section_body(section, character_class.name)
        if not body:
            continue
        block = f"#### {_title(section)}\n{body[:limit].rstrip()}"
        if used + len(block) > DOSSIER_CHAR_BUDGET:
            parts.append("El resto del texto de esta clase queda fuera de este contexto.")
            break
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)


def write_class_primer(catalog: ClassCatalog | None = None) -> str:
    """Guarda el resumen de las doce clases para revisarlo o reutilizarlo."""
    catalog = catalog or load_catalog()
    CLASS_PRIMER_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = (
        "Generado por python -m dnd_ai.classes a partir de data/json/clases.json.\n"
        "No editar a mano: vuelve a generar el archivo si cambia el JSON.\n\n"
        + render_primer(catalog)
    )
    CLASS_PRIMER_PATH.write_text(text, encoding="utf-8")
    return str(CLASS_PRIMER_PATH)


def _title(section: ClassSection) -> str:
    return normalize_srd_text(section.title)


def _section_body(section: ClassSection, class_name: str) -> str:
    match section.kind:
        case SectionKind.ATRIBUTOS:
            return ""
        case SectionKind.RASGO:
            return without_progression_table(section.body, class_name)
        case SectionKind.SECCION | SectionKind.ENCABEZADO | SectionKind.SUBCLASE:
            return normalize_srd_text(section.body)
        case _:
            assert_never(section.kind)


def _body_limit(kind: SectionKind) -> int:
    match kind:
        case SectionKind.ATRIBUTOS:
            return 0
        case SectionKind.RASGO:
            return 700
        case SectionKind.ENCABEZADO | SectionKind.SUBCLASE:
            return 500
        case SectionKind.SECCION:
            return 400
        case _:
            assert_never(kind)
