"""TTS interface."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Speech:
    text: str
    backend: str
    audio_path: str | None = None


class TTS:
    backend = "base"

    def synthesize(self, text: str) -> Speech:  # pragma: no cover - abstract
        raise NotImplementedError
