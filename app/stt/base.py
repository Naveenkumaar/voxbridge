"""STT interface."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Transcript:
    text: str
    backend: str


class STT:
    backend = "base"

    def transcribe(self, audio_or_text) -> Transcript:  # pragma: no cover - abstract
        raise NotImplementedError
