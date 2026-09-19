"""STT interface."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Transcript:
    text: str
    backend: str
    partial: bool = False   # True for interim results while the caller is still speaking


class STT:
    backend = "base"

    def transcribe(self, audio_or_text) -> Transcript:  # pragma: no cover - abstract
        raise NotImplementedError

    def stream(self, audio_or_text):
        """Yield interim transcripts, then the final one.

        Default: a single final transcript (no streaming). Backends that support
        partial results override this to emit growing prefixes so the pipeline
        can act before the caller finishes.
        """
        yield self.transcribe(audio_or_text)
