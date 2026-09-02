"""Script maestro para construir la base de conocimiento completa del SRD 5.2.1."""
from __future__ import annotations

from .extractor import extract_all
from .parsers import classes, glossary, rules
from .store import build_vector_store


def build_all() -> None:
    print("=== Step 1/5: Extrayendo texto del PDF ===")
    extract_all()

    print("\n=== Step 2/5: Parseando Glosario ===")
    g_items = glossary.build()
    print(f"Glosario: {len(g_items)} entradas en data/json/glosario.json")

    print("\n=== Step 3/5: Parseando Clases ===")
    c_items = classes.build()
    print(f"Clases: {len(c_items)} clases en data/json/clases.json")

    print("\n=== Step 4/5: Parseando Reglas ===")
    r_items = rules.build()
    print(f"Reglas: {len(r_items)} secciones en data/json/reglas.json")

    print("\n=== Step 5/5: Indexando en ChromaDB ===")
    total = build_vector_store()
    print(f"\n¡Base de conocimiento construida con éxito! Total de vectores: {total}")


if __name__ == "__main__":
    build_all()
