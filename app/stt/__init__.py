"""Speech-to-text stage (pluggable).

Default is a text passthrough so the whole agent runs offline with no models —
you type what you'd say. Set ``STT_BACKEND=whisper`` to transcribe real audio
with faster-whisper (optional dependency).
"""
from __future__ import annotations

import os


def get_stt():
    if os.getenv("STT_BACKEND", "text").lower() == "whisper":
        from .whisper_stt import WhisperSTT

        return WhisperSTT()
    from .stub import TextSTT

    return TextSTT()
