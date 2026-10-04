import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydub import AudioSegment
from pydub.generators import Sine

import recap_audio
from questions import QUESTIONS


class RecapAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.session_id = "session-test"
        self.responses_dir = self.root / "responses"
        self.recaps_dir = self.root / "recaps"
        self.session = {
            question["colonne_csv"]: "reponse"
            for question in QUESTIONS
        }
        self.segments = []

        for index, question in enumerate(QUESTIONS):
            question_path = self.root / question["chemin_audio"]
            response_path = self.responses_dir / self.session_id / f"{question['id']}.wav"
            self._write_tone(question_path, 440 + index * 100, 100 + index * 10)
            self._write_tone(response_path, 840 + index * 100, 140 + index * 10)
            self.segments.extend(
                [
                    self._load_normalized(question_path),
                    self._load_normalized(response_path),
                ]
            )

        self.patches = [
            patch.object(recap_audio, "PROJECT_DIR", self.root),
            patch.object(recap_audio, "REPONSES_DIR", self.responses_dir),
            patch.object(recap_audio, "RECAPS_DIR", self.recaps_dir),
            patch.object(recap_audio.csv_store, "lire_session", return_value=self.session),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.temp_dir.cleanup()

    def _write_tone(self, path, frequency, duration):
        path.parent.mkdir(parents=True, exist_ok=True)
        audio = Sine(frequency).to_audio_segment(duration=duration)
        audio = audio.set_channels(1).set_sample_width(2)
        with path.open("wb") as fichier_audio:
            audio.export(fichier_audio, format="wav")

    def _load_normalized(self, path):
        with path.open("rb") as fichier_audio:
            return (
                AudioSegment.from_file(fichier_audio)
                .set_frame_rate(recap_audio.FRAME_RATE)
                .set_channels(1)
                .set_sample_width(2)
            )

    def test_generates_ordered_recap_with_silence_and_caches_it(self):
        recap_path = recap_audio.generer_recap_audio(self.session_id)
        with recap_path.open("rb") as fichier_recap:
            recap = AudioSegment.from_file(fichier_recap)
        expected_duration = sum(len(segment) for segment in self.segments) + 7 * 500

        self.assertEqual(recap_path, self.recaps_dir / f"{self.session_id}.wav")
        self.assertAlmostEqual(len(recap), expected_duration, delta=2)

        offset = 0
        for segment in self.segments:
            actual = recap[offset:offset + len(segment)]
            self.assertEqual(actual.raw_data, segment.raw_data)
            offset += len(segment) + 500

        with patch.object(recap_audio.AudioSegment, "from_file", side_effect=AssertionError):
            same_path = recap_audio.generer_recap_audio(self.session_id)
        self.assertEqual(same_path, recap_path)

    def test_refuses_a_session_with_an_unanswered_question(self):
        self.session["telephone"] = ""

        with self.assertRaisesRegex(ValueError, "session n'est pas terminée"):
            recap_audio.generer_recap_audio(self.session_id)


if __name__ == "__main__":
    unittest.main()