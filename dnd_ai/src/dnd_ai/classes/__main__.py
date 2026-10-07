"""Muestra el catálogo de clases y escribe el contexto para el modelo."""
from __future__ import annotations

from .catalog import load_catalog
from .primer import write_class_primer


def main() -> None:
    catalog = load_catalog()
    path = write_class_primer(catalog)
    print(f"Clases del SRD 5.2.1: {len(catalog.all())}")
    for character_class in catalog.all():
        attributes = character_class.attributes()
        subclass = character_class.subclass()
        subclass_name = subclass.title if subclass is not None else "sin subclase"
        print(
            f"- {character_class.name}: {attributes.hit_die} | "
            f"{attributes.primary_ability} | {subclass_name}"
        )
    print(f"Contexto para el modelo: {path}")
    print("Guía para quien crea su primera clase: python -m dnd_ai.classes.beginner")


if __name__ == "__main__":
    main()
