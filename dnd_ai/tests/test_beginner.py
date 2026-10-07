"""La categoría Primera clase cubre el catálogo y no adelanta la subclase."""
from __future__ import annotations

import unittest

from dnd_ai.classes.beginner import (
    BEGINNER_CATEGORY,
    DEFAULT_FIRST_CLASS,
    LATER_CLASSES,
    casts_spells_at_level_one,
    class_for_wish,
    level_one_features,
    render_class_card,
    render_first_class_guide,
    subclass_level,
    suggest_door,
)
from dnd_ai.classes.catalog import SRD_CLASS_NAMES, load_catalog


class FirstClassGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()
        cls.guide = render_first_class_guide(cls.catalog)

    def test_category_names_every_class(self) -> None:
        self.assertIn(BEGINNER_CATEGORY, self.guide)
        for name in SRD_CLASS_NAMES:
            self.assertIn(name, self.guide)

    def test_lost_player_is_pointed_at_the_barbarian(self) -> None:
        self.assertEqual(DEFAULT_FIRST_CLASS, "Bárbaro")
        self.assertIn("Si no sabes qué quieres jugar, elige Bárbaro", self.guide)
        self.assertIn("el más alto de las doce", self.guide)
        self.assertIn("Ficha de hoy: Bárbaro", self.guide)

    def test_level_one_card_hides_later_features(self) -> None:
        card = render_class_card(self.catalog.get("Bárbaro"))
        self.assertIn("Furia", card)
        self.assertIn("1d12", card)
        self.assertIn("no se elige hoy", card)
        self.assertIn("nivel 3", card)
        self.assertNotIn("Campeón primordial", card)
        self.assertNotIn("lanza conjuros desde el nivel 1", card)

    def test_spell_classes_are_marked_and_martial_starters_are_not(self) -> None:
        for name in ("Bárbaro", "Guerrero", "Monje", "Pícaro"):
            self.assertFalse(casts_spells_at_level_one(self.catalog.get(name)), name)
        for name in ("Mago", "Clérigo", "Brujo", "Hechicero"):
            self.assertTrue(casts_spells_at_level_one(self.catalog.get(name)), name)
        self.assertTrue(level_one_features(self.catalog.get("Pícaro")))

    def test_subclass_waits_until_level_three(self) -> None:
        for character_class in self.catalog.all():
            self.assertEqual(subclass_level(character_class), 3, character_class.name)

    def test_a_wish_picks_one_door(self) -> None:
        delante = suggest_door("quiero pegar y aguantar con un hacha")
        astucia = suggest_door("quiero un pícaro que se esconda")
        magia = suggest_door("quiero lanzar conjuros")
        lost = suggest_door("no sé qué personaje hacer")
        self.assertIsNotNone(delante)
        self.assertIsNotNone(astucia)
        self.assertIsNotNone(magia)
        self.assertEqual(delante.start_class, "Bárbaro")
        self.assertEqual(astucia.start_class, "Pícaro")
        self.assertEqual(magia.start_class, "Clérigo")
        self.assertIsNone(lost)
        self.assertEqual(class_for_wish("quiero un guerrero con espada"), "Guerrero")
        self.assertEqual(class_for_wish("quiero ser mago"), "Mago")
        self.assertEqual(class_for_wish("no sé qué personaje hacer"), "Bárbaro")

    def test_later_classes_stay_out_of_the_first_doors(self) -> None:
        self.assertEqual(
            LATER_CLASSES,
            ("Bardo", "Brujo", "Druida", "Explorador", "Hechicero", "Paladín"),
        )
        self.assertIn("Cuando ya hayas jugado una clase", self.guide)


if __name__ == "__main__":
    unittest.main()
