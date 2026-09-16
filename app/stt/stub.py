"""Text passthrough STT — the offline default.

Treats its input as the already-transcribed text, so the dialogue and TTS
stages can be exercised end to end without any audio model.
"""
from __future__ import annotations

from .base import STT, Transcript


class TextSTT(STT):
    backend = "text"

    def transcribe(self, audio_or_text) -> Transcript:
        return Transcript(text=str(audio_or_text).strip(), backend=self.backend)
