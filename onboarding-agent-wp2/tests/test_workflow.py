import unittest
from unittest.mock import MagicMock, Mock, patch

import workflow


class WorkflowTests(unittest.TestCase):
    def test_short_wav_uses_separate_temporary_file(self):
        audio = MagicMock()
        audio.__len__.return_value = 1000
        silence = MagicMock()
        padded_audio = MagicMock()
        silence.__add__.return_value = padded_audio
        padded_audio.__add__.return_value = padded_audio

        with patch.object(workflow.AudioSegment, "from_file", return_value=audio), patch.object(
            workflow.AudioSegment, "silent", return_value=silence
        ):
            path = workflow.preparer_audio_court("reponse.wav")

        self.assertEqual(path, "reponse_padded.wav")
        padded_audio.export.assert_called_once_with(path, format="wav")

    def test_transcribes_and_cleans_up_short_audio(self):
        model = Mock()
        model.transcribe.return_value = {"text": "  Siliana  "}

        with patch.object(workflow.os.path, "exists", return_value=True), patch.object(
            workflow, "preparer_audio_court", return_value="reponse_padded.wav"
        ), patch.object(workflow, "obtenir_modele", return_value=model), patch.object(
            workflow.os, "remove"
        ) as remove:
            texte = workflow.transcrire_reponse_exacte("reponse.aac", "adresse")

        self.assertEqual(texte, "Siliana")
        self.assertEqual(model.transcribe.call_args.kwargs["temperature"], 0.0)
        self.assertIn("Siliana", model.transcribe.call_args.kwargs["initial_prompt"])
        remove.assert_called_once_with("reponse_padded.wav")

    def test_cleans_up_temporary_audio_when_transcription_fails(self):
        model = Mock()
        model.transcribe.side_effect = RuntimeError("transcription failed")

        with patch.object(workflow.os.path, "exists", return_value=True), patch.object(
            workflow, "preparer_audio_court", return_value="reponse_padded.wav"
        ), patch.object(workflow, "obtenir_modele", return_value=model), patch.object(
            workflow.os, "remove"
        ) as remove:
            with self.assertRaisesRegex(RuntimeError, "transcription failed"):
                workflow.transcrire_reponse_exacte("reponse.aac", "job")

        remove.assert_called_once_with("reponse_padded.wav")

    def test_missing_audio_returns_existing_error_message(self):
        with patch.object(workflow.os.path, "exists", return_value=False):
            result = workflow.transcrire_reponse_exacte("absent.aac")

        self.assertEqual(result, "Fichier introuvable : absent.aac")


if __name__ == "__main__":
    unittest.main()