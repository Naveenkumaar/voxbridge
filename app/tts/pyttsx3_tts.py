"""pyttsx3 offline TTS (optional) — synthesizes a WAV file on disk."""
from __future__ import annotations

import tempfile

from .base import TTS, Speech


class Pyttsx3TTS(TTS):
    backend = "pyttsx3"

    def __init__(self) -> None:
        import pyttsx3

        self.engine = pyttsx3.init()

    def synthesize(self, text: str) -> Speech:
        path = tempfile.mktemp(suffix=".wav")
        self.engine.save_to_file(text, path)
        self.engine.runAndWait()
        return Speech(text=text, backend=self.backend, audio_path=path)
