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

    def synthesize_stream(self, text: str):
        """Yield speech in chunks so the client can start speaking sooner.

        Default: a single chunk (the whole reply). Backends that support
        incremental synthesis override this to emit clause/sentence chunks.
        """
        yield self.synthesize(text)
