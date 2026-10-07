"""Categoría Primera clase: guía para quien elige clase por primera vez."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import Enum
from typing import assert_never

from ..config import FIRST_CLASS_GUIDE_PATH
from ..knowledge.parsers.common import unaccent
from .catalog import SRD_CLASS_NAMES, ClassCatalog, load_catalog
from .model import CharacterClass, ClassSection
from .text import normalize_srd_text

BEGINNER_CATEGORY = "primera_clase"
DEFAULT_FIRST_CLASS = "Bárbaro"

_LEVEL_ONE = re.compile(r"^Nivel\s*1:\s*(.+)$", re.IGNORECASE)
_SUBCLASS_LEVEL = re.compile(r"^Nivel\s*(\d+):\s*Subclase\b", re.IGNORECASE)
_DIE_FACES = re.compile(r"1d(\d+)")
_SPELL_MARKERS = ("lanzamiento de conjuros", "magia del pacto")


class DoorId(Enum):
    DELANTE = "delante"
    ASTUCIA = "astucia"
    MAGIA = "magia"


@dataclass(frozen=True)
class GuideDoor:
    door_id: DoorId
    title: str
    wish: str
    start_class: str
    other_classes: tuple[str, ...]
    keywords: tuple[str, ...]
    why: str


DOORS: tuple[GuideDoor, ...] = (
    GuideDoor(
        door_id=DoorId.DELANTE,
        title="Estar delante del grupo",
        wish="Quiero pegar de cerca y aguantar los golpes.",
        start_class="Bárbaro",
        other_classes=("Guerrero",),
        keywords=(
            "barbaro",
            "furia",
            "guerrero",
            "pegar",
            "golpear",
            "delante",
            "aguantar",
            "espada",
            "hacha",
            "fuerza",
        ),
        why=(
            "Empieza por el bárbaro. En nivel 1 su rasgo central es Furia: "
            "un momento claro en el que pegas más y aguantas más. No preparas conjuros. "
            "Si prefieres armadura y un estilo de combate en vez de furia, mira al guerrero."
        ),
    ),
    GuideDoor(
        door_id=DoorId.ASTUCIA,
        title="Moverte con astucia",
        wish="Quiero resolver la escena con precisión, no con la vida más alta.",
        start_class="Pícaro",
        other_classes=("Monje",),
        keywords=(
            "picaro",
            "furtivo",
            "sigilo",
            "ladron",
            "astucia",
            "monje",
            "esconder",
        ),
        why=(
            "Empieza por el pícaro. Tu característica es Destreza y tu rasgo central "
            "es Ataque furtivo: pegas mejor cuando tienes ventaja o un aliado junto al objetivo. "
            "Tampoco empiezas con conjuros. Si quieres pelear sin armadura, mira también al monje."
        ),
    ),
    GuideDoor(
        door_id=DoorId.MAGIA,
        title="Resolver las cosas con magia",
        wish="Quiero que mi clase lance conjuros desde el primer nivel.",
        start_class="Clérigo",
        other_classes=("Mago",),
        keywords=(
            "clerigo",
            "mago",
            "conjuro",
            "hechizo",
            "magia",
            "lanzar",
            "libro",
        ),
        why=(
            "Esta puerta pide leer un poco más, porque en nivel 1 ya hay conjuros. "
            "Si aun así es tu idea, empieza por el clérigo: su trabajo es sostener al grupo "
            "con Sabiduría. Si prefieres estudiar un libro, elige al mago y su Inteligencia."
        ),
    ),
)

LATER_CLASSES: tuple[str, ...] = (
    "Bardo",
    "Brujo",
    "Druida",
    "Explorador",
    "Hechicero",
    "Paladín",
)


def level_one_features(character_class: CharacterClass) -> tuple[ClassSection, ...]:
    found: list[ClassSection] = []
    for feature in character_class.class_features():
        if _LEVEL_ONE.match(normalize_srd_text(feature.title)):
            found.append(feature)
    return tuple(found)


def casts_spells_at_level_one(character_class: CharacterClass) -> bool:
    for feature in level_one_features(character_class):
        title = normalize_srd_text(feature.title).lower()
        if any(marker in title for marker in _SPELL_MARKERS):
            return True
    return False


def subclass_level(character_class: CharacterClass) -> int | None:
    for feature in character_class.class_features():
        match = _SUBCLASS_LEVEL.match(normalize_srd_text(feature.title))
        if match:
            return int(match.group(1))
    return None


def suggest_door(text: str) -> GuideDoor | None:
    """Elige una puerta a partir de lo que la persona dice que quiere jugar."""
    folded = unaccent(text).lower()
    best_score = 0
    best: GuideDoor | None = None
    for door in DOORS:
        score = sum(1 for word in door.keywords if word in folded)
        if any(_name_in(name, folded) for name in (door.start_class, *door.other_classes)):
            score += 5
        if score > best_score:
            best_score = score
            best = door
    return best


def class_for_wish(text: str) -> str:
    """Clase concreta para esa frase. Si no hay pista, devuelve el bárbaro."""
    door = suggest_door(text)
    if door is None:
        return DEFAULT_FIRST_CLASS
    folded = unaccent(text).lower()
    mentioned = [
        name
        for name in (door.start_class, *door.other_classes)
        if _name_in(name, folded)
    ]
    if len(mentioned) == 1:
        return mentioned[0]
    return door.start_class


def render_first_class_guide(catalog: ClassCatalog) -> str:
    _validate_coverage()
    default = catalog.get(DEFAULT_FIRST_CLASS)
    blocks = [
        f"# Categoría: {BEGINNER_CATEGORY}",
        "",
        "Esta guía es para quien va a crear su primera clase y no quiere perderse entre las doce.",
        "Una clase no es el personaje entero. Es la manera en que ese personaje resuelve los problemas.",
        "Hoy solo eliges la clase y lees el nivel 1. El resto de la tabla puede esperar.",
        "",
        _default_advice(catalog, default),
        "",
        "## Qué haces hoy",
        "",
        "1. Elige una puerta, o quédate con el bárbaro si ninguna te dice nada.",
        "2. Anota la característica principal. Es la que más vas a tirar.",
        "3. Anota el dado de puntos de golpe. Marca cuánta vida ganas al subir de nivel.",
        "4. Lee únicamente los rasgos que dicen Nivel 1.",
        "5. Deja la subclase para el nivel que indica la propia clase.",
        "",
        "## Tres puertas",
        "",
    ]
    for door in DOORS:
        blocks.append(_render_door(door, catalog))
        blocks.append("")
    blocks.append("## Cuando ya hayas jugado una clase")
    blocks.append("")
    blocks.append(
        "Estas seis también están en el libro. Conviene dejarlas para cuando "
        "el ritmo de la mesa ya no sea nuevo: varias combinan golpes y conjuros, "
        "o traen una lista extra que leer el primer día."
    )
    blocks.append("")
    for name in LATER_CLASSES:
        blocks.append(f"- {_later_line(catalog.get(name))}")
    blocks.append("")
    blocks.append("## Ficha de hoy: Bárbaro")
    blocks.append("")
    blocks.append(render_class_card(default))
    blocks.append("")
    return "\n".join(blocks).strip() + "\n"


def render_class_card(character_class: CharacterClass) -> str:
    attributes = character_class.attributes()
    lines = [
        f"### {character_class.name}",
        f"- Característica principal: {attributes.primary_ability}",
        f"- Dado de puntos de golpe: {attributes.hit_die}",
        f"- Tiradas de salvación: {attributes.saving_throws}",
    ]
    if attributes.armor_training:
        lines.append(f"- Armadura: {attributes.armor_training}")
    lines.append("- Rasgos que usas en nivel 1:")
    features = level_one_features(character_class)
    if not features:
        lines.append("  - Esta clase no tiene rasgos marcados como Nivel 1 en el catálogo.")
    for feature in features:
        lines.append(f"  - {_feature_label(feature)}")
    note = _creation_note(character_class)
    if note:
        lines.append(f"- Al crear el personaje, el libro dice: {note}")
    level = subclass_level(character_class)
    subclass = character_class.subclass()
    if level is not None and subclass is not None:
        lines.append(
            "- La subclase no se elige hoy. "
            f"Llega en el nivel {level}. "
            f"El ejemplo del libro es: {normalize_srd_text(subclass.title)}."
        )
    if casts_spells_at_level_one(character_class):
        lines.append(
            "- Esta clase lanza conjuros desde el nivel 1. "
            "Si es tu primera partida y eso te abruma, vuelve a la puerta del bárbaro o del pícaro."
        )
    return "\n".join(lines)


def write_first_class_guide(catalog: ClassCatalog | None = None) -> str:
    catalog = catalog or load_catalog()
    FIRST_CLASS_GUIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = render_first_class_guide(catalog)
    FIRST_CLASS_GUIDE_PATH.write_text(text, encoding="utf-8")
    return str(FIRST_CLASS_GUIDE_PATH)


def main() -> None:
    catalog = load_catalog()
    path = write_first_class_guide(catalog)
    argument = " ".join(sys.argv[1:]).strip()
    if not argument:
        print(render_first_class_guide(catalog))
        print(f"Guía guardada en: {path}")
        return
    try:
        chosen = catalog.get(argument)
    except KeyError:
        chosen = None
    if chosen is not None:
        print(render_class_card(chosen))
        if chosen.name in LATER_CLASSES:
            print(
                "\nPuedes dejar esta clase para más adelante. "
                "Si es tu primera partida, entra por el bárbaro, el pícaro o el clérigo."
            )
        return
    door = suggest_door(argument)
    if door is None:
        print("No encontré una preferencia clara. Quédate con el bárbaro para esta primera clase.")
        print(render_class_card(catalog.get(DEFAULT_FIRST_CLASS)))
        return
    print(_render_door(door, catalog))
    print()
    print(render_class_card(catalog.get(class_for_wish(argument))))


def _default_advice(catalog: ClassCatalog, default: CharacterClass) -> str:
    faces = _die_faces(default.attributes().hit_die)
    highest = max(_die_faces(item.attributes().hit_die) for item in catalog.all())
    if faces == highest and faces > 0:
        die_note = f"Su dado de golpe es {default.attributes().hit_die}, el más alto de las doce."
    else:
        die_note = f"Su dado de golpe es {default.attributes().hit_die}."
    return (
        f"Si no sabes qué quieres jugar, elige {default.name}. {die_note} "
        "No preparas conjuros en el nivel 1. Puedes cambiar de idea antes de sentarte a la mesa."
    )


def _render_door(door: GuideDoor, catalog: ClassCatalog) -> str:
    start = catalog.get(door.start_class)
    others = ", ".join(door.other_classes)
    lines = [
        f"### {door.title}",
        door.wish,
        door.why,
        (
            f"Clase para empezar: {start.name} "
            f"({start.attributes().primary_ability}; {start.attributes().hit_die})."
        ),
        f"También en esta puerta: {others}.",
    ]
    match door.door_id:
        case DoorId.DELANTE | DoorId.ASTUCIA:
            lines.append("En esta puerta no hace falta aprender conjuros para jugar el primer nivel.")
        case DoorId.MAGIA:
            lines.append("Entra aquí solo si te apetece leer conjuros en la primera sesión.")
        case _:
            assert_never(door.door_id)
    return "\n".join(lines)


def _later_line(character_class: CharacterClass) -> str:
    attributes = character_class.attributes()
    labels = ", ".join(_feature_label(feature) for feature in level_one_features(character_class))
    spells = (
        "En nivel 1 ya lanza conjuros."
        if casts_spells_at_level_one(character_class)
        else "En nivel 1 no lanza conjuros."
    )
    return (
        f"{character_class.name}: característica {attributes.primary_ability}, "
        f"dado {attributes.hit_die}. {spells} Rasgos de nivel 1: {labels}."
    )


def _feature_label(feature: ClassSection) -> str:
    title = normalize_srd_text(feature.title)
    match = _LEVEL_ONE.match(title)
    if match:
        return match.group(1).strip()
    return title


def _creation_note(character_class: CharacterClass) -> str:
    for section in character_class.option_headings():
        title = normalize_srd_text(section.title).lower()
        if title.startswith("como personaje de nivel 1"):
            return normalize_srd_text(section.body)
    return ""


def _name_in(name: str, folded_text: str) -> bool:
    return unaccent(name).lower() in folded_text


def _die_faces(hit_die: str) -> int:
    match = _DIE_FACES.search(hit_die)
    if match is None:
        return 0
    return int(match.group(1))


def _validate_coverage() -> None:
    door_ids = [door.door_id for door in DOORS]
    if set(door_ids) != set(DoorId) or len(door_ids) != len(set(door_ids)):
        raise RuntimeError("Las puertas de la guía Primera clase están incompletas o repetidas.")
    starts = [door.start_class for door in DOORS]
    if DEFAULT_FIRST_CLASS not in starts:
        raise RuntimeError(
            f"La clase por defecto ({DEFAULT_FIRST_CLASS}) tiene que ser el inicio de una puerta."
        )
    placed: list[str] = []
    for door in DOORS:
        placed.append(door.start_class)
        placed.extend(door.other_classes)
    placed.extend(LATER_CLASSES)
    if len(placed) != len(set(placed)):
        raise RuntimeError(f"Hay clases repetidas en la guía Primera clase: {placed}")
    if set(placed) != set(SRD_CLASS_NAMES):
        missing = [name for name in SRD_CLASS_NAMES if name not in placed]
        extra = [name for name in placed if name not in SRD_CLASS_NAMES]
        raise RuntimeError(
            "La guía Primera clase no cubre el catálogo. "
            f"Faltan: {missing or 'ninguna'}. Sobran: {extra or 'ninguna'}."
        )


if __name__ == "__main__":
    main()
