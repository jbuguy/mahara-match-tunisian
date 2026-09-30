import unittest
from unittest.mock import patch

from offre_generator import generer_offre_ecrite


class OffreGeneratorTests(unittest.TestCase):
    def test_replaces_the_four_template_values(self):
        session = {
            "metier": "agriculture",
            "date_disponibilite": "2 octobre",
            "gouvernorat": "Siliana",
            "telephone": "91131139",
        }

        with patch("offre_generator.csv_store.lire_session", return_value=session):
            offre = generer_offre_ecrite("session-1")

        self.assertIn("Métier recherché : agriculture", offre)
        self.assertIn("Date de disponibilité : 2 octobre", offre)
        self.assertIn("Gouvernorat : Siliana", offre)
        self.assertIn("Téléphone : 91131139", offre)
        self.assertNotIn("{", offre)

    def test_empty_values_are_reported_as_unspecified(self):
        session = {
            "metier": " ",
            "date_disponibilite": "",
            "gouvernorat": None,
            "telephone": "  ",
        }

        with patch("offre_generator.csv_store.lire_session", return_value=session):
            offre = generer_offre_ecrite("session-2")

        self.assertEqual(offre.count("non précisé"), 4)


if __name__ == "__main__":
    unittest.main()