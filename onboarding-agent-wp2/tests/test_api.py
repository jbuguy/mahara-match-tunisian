import io
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app import api
from questions import QUESTIONS


def wav_bytes():
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 8000)
    return output.getvalue()


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.patches = [
            patch.object(api, "initialiser_moteur_stt"),
            patch.object(api, "SESSIONS_CSV", root / "sessions.csv"),
            patch.object(api, "REPONSES_DIR", root / "audio_reponses"),
            patch.object(
                api,
                "transcrire_et_extraire",
                return_value={"texte_brut": "نجار", "valeur_extraite": "نجار"},
            ),
        ]
        for patcher in self.patches:
            patcher.start()
        self.client = TestClient(api.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp_dir.cleanup()

    def create_session(self):
        response = self.client.post("/api/v1/sessions")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def complete_session(self, session_id):
        for question in QUESTIONS:
            api.csv_store.enregistrer_reponse(
                session_id,
                question["id"],
                "reponse de test",
                api.SESSIONS_CSV,
            )

    def test_creates_session_and_returns_current_question(self):
        created = self.create_session()

        self.assertEqual(created["question"]["id"], "metier")
        self.assertEqual(created["question"]["audio_url"], "/audio/questions/metier")
        current = self.client.get(
            f"/api/v1/sessions/{created['session_id']}/question"
        )
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json()["question"]["id"], "metier")

    def test_serves_existing_question_audio(self):
        for question in QUESTIONS:
            response = self.client.get(f"/audio/questions/{question['id']}")

            self.assertEqual(response.status_code, 200, question["id"])
            self.assertTrue(response.content, question["id"])

    def test_session_finishes_after_four_answers(self):
        session = self.create_session()
        self.assertEqual(len(QUESTIONS), 4)
        self.assertTrue(all(question["audio_url"] for question in [
            self.client.get(
                f"/api/v1/sessions/{session['session_id']}/question"
            ).json()["question"]
        ]))

        for index, question in enumerate(QUESTIONS):
            response = self.client.post(
                f"/api/v1/sessions/{session['session_id']}/reponse",
                files={"audio": ("answer.wav", wav_bytes(), "audio/wav")},
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()
            if index < 3:
                self.assertEqual(body["question_suivante"]["id"], QUESTIONS[index + 1]["id"])
                self.assertTrue(body["question_suivante"]["audio_url"])
                self.assertFalse(body["termine"])
            else:
                self.assertIsNone(body["question_suivante"])
                self.assertTrue(body["termine"])

        current = self.client.get(
            f"/api/v1/sessions/{session['session_id']}/question"
        )
        self.assertEqual(current.json(), {"termine": True, "question": None})

    def test_empty_upload_returns_retryable_error_without_advancing(self):
        session = self.create_session()
        response = self.client.post(
            f"/api/v1/sessions/{session['session_id']}/reponse",
            files={"audio": ("silence.wav", b"", "audio/wav")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"]["code"], "audio_vide")
        current = self.client.get(
            f"/api/v1/sessions/{session['session_id']}/question"
        )
        self.assertEqual(current.json()["question"]["id"], "metier")

    def test_empty_transcription_retry_promotes_only_the_accepted_audio(self):
        session = self.create_session()
        with patch.object(
            api,
            "transcrire_et_extraire",
            return_value={"texte_brut": "   ", "valeur_extraite": None},
        ):
            response = self.client.post(
                f"/api/v1/sessions/{session['session_id']}/reponse",
                files={"audio": ("answer.wav", wav_bytes(), "audio/wav")},
            )

        self.assertEqual(response.status_code, 422)
        self.assertTrue(response.json()["detail"]["reessayer"])
        current = self.client.get(
            f"/api/v1/sessions/{session['session_id']}/question"
        )
        self.assertEqual(current.json()["question"]["id"], "metier")
        accepted_audio = api.REPONSES_DIR / session["session_id"] / "metier.wav"
        self.assertFalse(accepted_audio.exists())

        retry = self.client.post(
            f"/api/v1/sessions/{session['session_id']}/reponse",
            files={"audio": ("answer.wav", wav_bytes(), "audio/wav")},
        )

        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["question_suivante"]["id"], "date")
        self.assertTrue(accepted_audio.is_file())

    def test_success_stores_answer_and_returns_next_question(self):
        session = self.create_session()
        response = self.client.post(
            f"/api/v1/sessions/{session['session_id']}/reponse",
            files={"audio": ("answer.wav", wav_bytes(), "audio/wav")},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["texte_brut"], "نجار")
        self.assertEqual(body["valeur_extraite"], "نجار")
        self.assertEqual(body["question_suivante"]["id"], "date")
        self.assertFalse(body["termine"])
        saved = api.csv_store.lire_session(session["session_id"], api.SESSIONS_CSV)
        self.assertEqual(saved["metier"], "نجار")
        recordings = api.REPONSES_DIR / session["session_id"]
        self.assertEqual([path.name for path in recordings.iterdir()], ["metier.wav"])

    def test_webm_upload_is_converted_before_transcription(self):
        session = self.create_session()
        decoded = Mock()
        decoded.__len__ = Mock(return_value=1000)
        decoded.export.side_effect = lambda path, format: Path(path).write_bytes(wav_bytes())

        with patch.object(api.AudioSegment, "from_file", return_value=decoded):
            response = self.client.post(
                f"/api/v1/sessions/{session['session_id']}/reponse",
                files={"audio": ("answer.webm", b"webm-data", "audio/webm")},
            )

        self.assertEqual(response.status_code, 200)
        decoded.export.assert_called_once()
        transcribe_call = api.transcrire_et_extraire.call_args
        self.assertTrue(transcribe_call.args[0].endswith(".wav"))

    def test_unknown_session_returns_404(self):
        response = self.client.get("/api/v1/sessions/missing/question")

        self.assertEqual(response.status_code, 404)

    def test_offer_and_recap_reject_incomplete_sessions(self):
        offer_session = self.create_session()
        recap_session = self.create_session()

        offer = self.client.get(
            f"/api/v1/sessions/{offer_session['session_id']}/offre"
        )
        recap = self.client.get(
            f"/api/v1/sessions/{recap_session['session_id']}/recap-audio"
        )

        self.assertEqual(offer.status_code, 409)
        self.assertIn("terminée", offer.json()["detail"])
        self.assertEqual(recap.status_code, 409)
        self.assertIn("terminée", recap.json()["detail"])

    def test_offer_and_recap_return_404_for_unknown_sessions(self):
        for endpoint in ("offre", "recap-audio"):
            with self.subTest(endpoint=endpoint):
                response = self.client.get(
                    f"/api/v1/sessions/missing/{endpoint}"
                )
                self.assertEqual(response.status_code, 404)

    def test_offer_and_recap_return_success_for_completed_sessions(self):
        session = self.create_session()
        self.complete_session(session["session_id"])

        with patch.object(api, "generer_offre_ecrite", return_value="Offre de test"):
            offer = self.client.get(
                f"/api/v1/sessions/{session['session_id']}/offre"
            )
        self.assertEqual(offer.status_code, 200)
        self.assertEqual(offer.text, "Offre de test")

        recap_path = Path(self.temp_dir.name) / "recap.wav"
        recap_path.write_bytes(wav_bytes())
        with patch.object(api, "generer_recap_audio", return_value=recap_path):
            recap = self.client.get(
                f"/api/v1/sessions/{session['session_id']}/recap-audio"
            )
        self.assertEqual(recap.status_code, 200)
        self.assertEqual(recap.headers["content-type"], "audio/wav")
        self.assertEqual(recap.content, wav_bytes())


if __name__ == "__main__":
    unittest.main()