import csv
import tempfile
import unittest
from pathlib import Path

from csv_store import CSV_COLUMNS, creer_session, enregistrer_reponse, lire_session


class CsvStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "sessions.csv"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_creates_csv_with_headers_and_session_metadata(self):
        session = creer_session(self.csv_path)

        self.assertTrue(session["session_id"])
        self.assertTrue(session["horodatage"])
        with self.csv_path.open("r", newline="", encoding="utf-8") as fichier:
            lecteur = csv.DictReader(fichier)
            self.assertEqual(lecteur.fieldnames, CSV_COLUMNS)
            ligne = next(lecteur)
        self.assertEqual(ligne["session_id"], session["session_id"])
        self.assertEqual(ligne["metier"], "")

    def test_saves_answer_in_question_column_and_reads_session(self):
        session = creer_session(self.csv_path)

        enregistrer_reponse(
            session["session_id"], "gouvernorat", "سليانة", self.csv_path
        )
        ligne = lire_session(session["session_id"], self.csv_path)

        self.assertEqual(ligne["gouvernorat"], "سليانة")
        self.assertEqual(ligne["metier"], "")

    def test_rejects_unknown_question(self):
        session = creer_session(self.csv_path)

        with self.assertRaisesRegex(ValueError, "Question inconnue"):
            enregistrer_reponse(session["session_id"], "inconnue", "x", self.csv_path)

    def test_rejects_unknown_session_when_saving_or_reading(self):
        with self.assertRaisesRegex(KeyError, "Session introuvable"):
            lire_session("missing", self.csv_path)

        session = creer_session(self.csv_path)
        with self.assertRaisesRegex(KeyError, "Session introuvable"):
            enregistrer_reponse("missing", "date", "2 octobre", self.csv_path)

    def test_removes_free_text_column_and_preserves_other_data(self):
        with self.csv_path.open("w", newline="", encoding="utf-8") as fichier:
            writer = csv.DictWriter(
                fichier,
                fieldnames=["session_id", "horodatage", "metier", "texte_libre", "custom"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "session_id": "existing-session",
                    "horodatage": "2026-09-30T10:00:00+00:00",
                    "metier": "menuisier",
                    "texte_libre": "à supprimer",
                    "custom": "à conserver",
                }
            )

        creer_session(self.csv_path)

        with self.csv_path.open("r", newline="", encoding="utf-8") as fichier:
            reader = csv.DictReader(fichier)
            self.assertNotIn("texte_libre", reader.fieldnames)
            self.assertIn("custom", reader.fieldnames)
            existing = next(reader)
        self.assertEqual(existing["metier"], "menuisier")
        self.assertEqual(existing["custom"], "à conserver")


if __name__ == "__main__":
    unittest.main()