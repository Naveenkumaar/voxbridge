"""Text TTS — the offline default. Returns the words that would be spoken."""
from __future__ import annotations

import re

from .base import TTS, Speech

_SENTENCE = re.compile(r"[^.!?]+[.!?]?")


class TextTTS(TTS):
    backend = "text"

    def synthesize(self, text: str) -> Speech:
        return Speech(text=text, backend=self.backend, audio_path=None)

    def synthesize_stream(self, text: str):
        """Emit one chunk per sentence so playback can begin on the first one."""
        chunks = [m.group().strip() for m in _SENTENCE.finditer(text) if m.group().strip()]
        for chunk in chunks or [text]:
            yield Speech(text=chunk, backend=self.backend, audio_path=None)
