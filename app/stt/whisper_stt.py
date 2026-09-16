"""faster-whisper STT (optional).

Transcribes a path to a WAV/MP3 file. Requires ``pip install faster-whisper``.
Model size and device are configurable via env vars.
"""
from __future__ import annotations

import os

from .base import STT, Transcript


class WhisperSTT(STT):
    backend = "whisper"

    def __init__(self) -> None:
        from faster_whisper import WhisperModel

        size = os.getenv("WHISPER_MODEL", "base.en")
        device = os.getenv("WHISPER_DEVICE", "cpu")
        self.model = WhisperModel(size, device=device, compute_type="int8")

    def transcribe(self, audio_path) -> Transcript:
        segments, _ = self.model.transcribe(str(audio_path))
        text = " ".join(seg.text for seg in segments).strip()
        return Transcript(text=text, backend=self.backend)
