"""Clases de personaje del SRD 5.2.1."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .text import normalize_srd_text


class SectionKind(Enum):
    ATRIBUTOS = "atributos"
    SECCION = "seccion"
    ENCABEZADO = "encabezado"
    RASGO = "rasgo"
    SUBCLASE = "subclase"


def parse_section_kind(value: str) -> SectionKind:
    try:
        return SectionKind(value)
    except ValueError as exc:
        known = ", ".join(kind.value for kind in SectionKind)
        raise ValueError(f"Tipo de sección desconocido: {value!r}. Esperados: {known}") from exc


@dataclass(frozen=True)
class ClassAttributes:
    primary_ability: str
    hit_die: str
    saving_throws: str
    skills: str
    weapons: str
    tools: str
    armor_training: str
    starting_equipment: str
    extra: tuple[tuple[str, str], ...] = ()

    @classmethod
    def from_metadata(cls, metadata: tuple[tuple[str, str], ...]) -> ClassAttributes:
        lookup = dict(metadata)
        known = {
            "Característica principal",
            "Dado de puntos de golpe",
            "Competencias en tiradas de salvación",
            "Competencias en habilidades",
            "Competencias con armas",
            "Competencias con herramientas",
            "Entrenamiento con armaduras",
            "Equipo inicial",
        }

        def take(label: str) -> str:
            return normalize_srd_text(lookup.get(label, ""))

        extra = tuple(
            (label, normalize_srd_text(value))
            for label, value in metadata
            if label not in known and normalize_srd_text(value)
        )
        return cls(
            primary_ability=take("Característica principal"),
            hit_die=take("Dado de puntos de golpe"),
            saving_throws=take("Competencias en tiradas de salvación"),
            skills=take("Competencias en habilidades"),
            weapons=take("Competencias con armas"),
            tools=take("Competencias con herramientas"),
            armor_training=take("Entrenamiento con armaduras"),
            starting_equipment=take("Equipo inicial"),
            extra=extra,
        )

    def labeled(self) -> tuple[tuple[str, str], ...]:
        rows = (
            ("Característica principal", self.primary_ability),
            ("Dado de puntos de golpe", self.hit_die),
            ("Competencias en tiradas de salvación", self.saving_throws),
            ("Competencias en habilidades", self.skills),
            ("Competencias con armas", self.weapons),
            ("Competencias con herramientas", self.tools),
            ("Entrenamiento con armaduras", self.armor_training),
            ("Equipo inicial", self.starting_equipment),
        )
        return rows + self.extra


@dataclass(frozen=True)
class ClassSection:
    title: str
    kind: SectionKind
    body: str
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class CharacterClass:
    name: str
    class_id: str
    sections: tuple[ClassSection, ...]

    def attributes(self) -> ClassAttributes:
        for section in self.sections:
            if section.kind is SectionKind.ATRIBUTOS:
                return ClassAttributes.from_metadata(section.metadata)
        raise ValueError(f"La clase {self.name} no tiene atributos básicos")

    def subclass(self) -> ClassSection | None:
        index = self._subclass_index()
        if index is None:
            return None
        return self.sections[index]

    def class_features(self) -> tuple[ClassSection, ...]:
        return tuple(
            section
            for section in self._before_subclass()
            if section.kind is SectionKind.RASGO
        )

    def option_headings(self) -> tuple[ClassSection, ...]:
        return tuple(
            section
            for section in self._before_subclass()
            if section.kind is SectionKind.ENCABEZADO
        )

    def subclass_features(self) -> tuple[ClassSection, ...]:
        index = self._subclass_index()
        if index is None:
            return ()
        return tuple(
            section
            for section in self.sections[index + 1 :]
            if section.kind is SectionKind.RASGO
        )

    def _subclass_index(self) -> int | None:
        for index, section in enumerate(self.sections):
            if section.kind is SectionKind.SUBCLASE:
                return index
        return None

    def _before_subclass(self) -> tuple[ClassSection, ...]:
        index = self._subclass_index()
        if index is None:
            return self.sections
        return self.sections[:index]
