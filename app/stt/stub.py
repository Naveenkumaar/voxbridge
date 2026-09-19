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

    def stream(self, audio_or_text):
        """Simulate streaming by emitting growing word-prefixes, then the final."""
        words = str(audio_or_text).strip().split()
        for i in range(1, len(words)):
            yield Transcript(text=" ".join(words[:i]), backend=self.backend, partial=True)
        yield Transcript(text=" ".join(words), backend=self.backend, partial=False)
