"""Carga las doce clases del SRD desde el JSON ya parseado."""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..config import JSON_DIR
from ..knowledge.parsers.common import slugify
from .model import CharacterClass, ClassSection, parse_section_kind
from .text import normalize_srd_text

SRD_CLASS_NAMES: tuple[str, ...] = (
    "Bárbaro",
    "Bardo",
    "Brujo",
    "Clérigo",
    "Druida",
    "Explorador",
    "Guerrero",
    "Hechicero",
    "Mago",
    "Monje",
    "Paladín",
    "Pícaro",
)


@dataclass(frozen=True)
class ClassCatalog:
    classes: tuple[CharacterClass, ...]

    def all(self) -> tuple[CharacterClass, ...]:
        return self.classes

    def get(self, name: str) -> CharacterClass:
        key = slugify(name)
        for character_class in self.classes:
            if slugify(character_class.name) == key or character_class.class_id == key:
                return character_class
        known = ", ".join(character_class.name for character_class in self.classes)
        raise KeyError(f"No existe la clase {name!r}. Clases del SRD: {known}")

    def mentioned_in(self, question: str) -> tuple[CharacterClass, ...]:
        folded = _fold(question)
        found: list[CharacterClass] = []
        for character_class in self.classes:
            if _fold(character_class.name) in folded:
                found.append(character_class)
        return tuple(found)


def load_catalog() -> ClassCatalog:
    path = JSON_DIR / "clases.json"
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra el catálogo de clases: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path} no contiene una lista de clases")

    by_name: dict[str, CharacterClass] = {}
    for item in raw:
        character_class = _parse_class(item)
        by_name[character_class.name] = character_class

    missing = [name for name in SRD_CLASS_NAMES if name not in by_name]
    extra = [name for name in by_name if name not in SRD_CLASS_NAMES]
    if missing or extra:
        raise ValueError(
            "El JSON de clases no coincide con el SRD 5.2.1. "
            f"Faltan: {missing or 'ninguna'}. Sobran: {extra or 'ninguna'}."
        )

    ordered = tuple(by_name[name] for name in SRD_CLASS_NAMES)
    catalog = ClassCatalog(ordered)
    for character_class in catalog.all():
        attributes = character_class.attributes()
        if not attributes.primary_ability or not attributes.hit_die:
            raise ValueError(
                f"{character_class.name} no tiene característica principal o dado de golpe"
            )
        if character_class.subclass() is None:
            raise ValueError(f"{character_class.name} no tiene subclase de ejemplo")
    return catalog


def _parse_class(item: object) -> CharacterClass:
    if not isinstance(item, dict):
        raise ValueError("Cada clase debe ser un objeto JSON")
    name = item.get("clase")
    class_id = item.get("id")
    sections = item.get("secciones")
    if not isinstance(name, str) or not isinstance(class_id, str) or not isinstance(sections, list):
        raise ValueError(f"Clase mal formada: {name!r}")
    parsed_sections = tuple(_parse_section(section) for section in sections)
    return CharacterClass(
        name=normalize_srd_text(name),
        class_id=class_id,
        sections=parsed_sections,
    )


def _parse_section(item: object) -> ClassSection:
    if not isinstance(item, dict):
        raise ValueError("Cada sección de clase debe ser un objeto JSON")
    title = item.get("titulo")
    kind = item.get("tipo")
    if not isinstance(title, str) or not isinstance(kind, str):
        raise ValueError("Sección de clase sin título o tipo")
    metadata = item.get("metadatos") or {}
    if not isinstance(metadata, dict):
        raise ValueError(f"Metadatos inválidos en {title!r}")
    body = item.get("contenido") or ""
    if not isinstance(body, str):
        raise ValueError(f"Contenido inválido en {title!r}")
    pairs = tuple(
        (str(label), str(value))
        for label, value in metadata.items()
    )
    return ClassSection(
        title=title,
        kind=parse_section_kind(kind),
        body=body,
        metadata=pairs,
    )


def _fold(text: str) -> str:
    return slugify(text).replace("-", " ")
