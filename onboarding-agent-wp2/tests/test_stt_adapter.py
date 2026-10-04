import sys
import types
import unittest
from unittest.mock import Mock, patch

from stt_adapter import transcrire_et_extraire


class SttAdapterTests(unittest.TestCase):
    def test_calls_existing_extractor_and_returns_expected_fields(self):
        existing_transcriber = Mock(
            return_value=types.SimpleNamespace(
                texte_brut="نجار", valeur_normalisee="نجار"
            )
        )
        fake_transcription = types.SimpleNamespace(
            transcrire_reponse_exacte=existing_transcriber
        )

        with patch.dict(sys.modules, {"transcription": fake_transcription}):
            result = transcrire_et_extraire("answer.aac", "métier")

        existing_transcriber.assert_called_once_with("answer.aac", "job")
        self.assertEqual(
            result,
            {"texte_brut": "نجار", "valeur_extraite": "نجار"},
        )

    def test_maps_free_text_to_existing_transcription_fallback(self):
        existing_transcriber = Mock(
            return_value=types.SimpleNamespace(
                texte_brut="réponse libre", valeur_normalisee="réponse libre"
            )
        )
        fake_transcription = types.SimpleNamespace(
            transcrire_reponse_exacte=existing_transcriber
        )

        with patch.dict(sys.modules, {"transcription": fake_transcription}):
            result = transcrire_et_extraire("answer.aac", "texte libre")

        existing_transcriber.assert_called_once_with("answer.aac", "")
        self.assertEqual(result["valeur_extraite"], "réponse libre")

    def test_rejects_unknown_response_type(self):
        with self.assertRaisesRegex(ValueError, "non pris en charge"):
            transcrire_et_extraire("answer.aac", "unknown")


if __name__ == "__main__":
    unittest.main()