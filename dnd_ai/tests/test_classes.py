"""Pruebas del catálogo de clases y del contexto que recibe el modelo."""
from __future__ import annotations

import unittest

from dnd_ai.classes.catalog import SRD_CLASS_NAMES, load_catalog
from dnd_ai.classes.primer import render_dossier, render_primer
from dnd_ai.llm.class_teacher import build_messages

EXPECTED_PRIMARY = {
    "Bárbaro": "Fuerza",
    "Bardo": "Carisma",
    "Brujo": "Carisma",
    "Clérigo": "Sabiduría",
    "Druida": "Sabiduría",
    "Explorador": "Destreza y Sabiduría",
    "Guerrero": "Fuerza o Destreza",
    "Hechicero": "Carisma",
    "Mago": "Inteligencia",
    "Monje": "Destreza y Sabiduría",
    "Paladín": "Fuerza y Carisma",
    "Pícaro": "Destreza",
}

EXPECTED_HIT_DIE = {
    "Bárbaro": "1d12",
    "Bardo": "1d8",
    "Brujo": "1d8",
    "Clérigo": "1d8",
    "Druida": "1d8",
    "Explorador": "1d10",
    "Guerrero": "1d10",
    "Hechicero": "1d6",
    "Mago": "1d6",
    "Monje": "1d8",
    "Paladín": "1d10",
    "Pícaro": "1d8",
}


class ClassCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()

    def test_loads_the_twelve_srd_classes(self) -> None:
        names = tuple(character_class.name for character_class in self.catalog.all())
        self.assertEqual(names, SRD_CLASS_NAMES)

    def test_each_class_has_identity_features_and_example_subclass(self) -> None:
        for character_class in self.catalog.all():
            attributes = character_class.attributes()
            self.assertEqual(attributes.primary_ability, EXPECTED_PRIMARY[character_class.name])
            self.assertIn(EXPECTED_HIT_DIE[character_class.name], attributes.hit_die)
            self.assertTrue(character_class.class_features())
            self.assertIsNotNone(character_class.subclass())
            self.assertTrue(character_class.subclass_features())

    def test_lookup_accepts_accents_and_case(self) -> None:
        self.assertEqual(self.catalog.get("mago").name, "Mago")
        self.assertEqual(self.catalog.get("MAGO").name, "Mago")
        self.assertEqual(self.catalog.get("paladin").name, "Paladín")
        self.assertEqual(self.catalog.get("clases-picaro").name, "Pícaro")

    def test_unknown_class_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.catalog.get("artífice")

    def test_barbarian_has_no_tool_proficiency(self) -> None:
        self.assertEqual(self.catalog.get("bárbaro").attributes().tools, "")

    def test_question_detects_named_classes(self) -> None:
        found = self.catalog.mentioned_in("¿En qué se diferencia un mago de un hechicero?")
        self.assertEqual(tuple(item.name for item in found), ("Hechicero", "Mago"))


class ClassContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog()

    def test_primer_names_every_class_and_its_hit_die(self) -> None:
        primer = render_primer(self.catalog)
        for name, hit_die in EXPECTED_HIT_DIE.items():
            self.assertIn(name, primer)
            self.assertIn(hit_die, primer)
        self.assertIn("Senda del berserker", primer)
        self.assertIn("Patrón infernal", primer)

    def test_general_question_feeds_all_twelve_classes(self) -> None:
        messages = build_messages("¿Qué clases existen?", self.catalog)
        system = messages[0]["content"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["content"], "¿Qué clases existen?")
        for name in SRD_CLASS_NAMES:
            self.assertIn(name, system)
        self.assertLess(len(system), 9000)

    def test_named_question_feeds_that_class_text(self) -> None:
        messages = build_messages("Explica la furia del bárbaro", self.catalog)
        system = messages[0]["content"]
        self.assertIn("Furia", system)
        self.assertIn("Bárbaro", system)
        self.assertNotIn("Hechicero", system)
        dossier = render_dossier(self.catalog.get("bárbaro"))
        self.assertIn("furia", dossier.lower())

    def test_empty_question_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_messages("   ", self.catalog)


if __name__ == "__main__":
    unittest.main()
