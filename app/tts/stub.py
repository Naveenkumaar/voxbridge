"""Text TTS — the offline default. Returns the words that would be spoken."""
from __future__ import annotations

from .base import TTS, Speech


class TextTTS(TTS):
    backend = "text"

    def synthesize(self, text: str) -> Speech:
        return Speech(text=text, backend=self.backend, audio_path=None)
