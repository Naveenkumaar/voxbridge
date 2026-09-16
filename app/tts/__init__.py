"""Text-to-speech stage (pluggable).

Default returns the spoken text plus metadata (no audio), so the pipeline runs
anywhere. Set ``TTS_BACKEND=pyttsx3`` to synthesize offline audio to a WAV file.
"""
from __future__ import annotations

import os


def get_tts():
    if os.getenv("TTS_BACKEND", "text").lower() == "pyttsx3":
        from .pyttsx3_tts import Pyttsx3TTS

        return Pyttsx3TTS()
    from .stub import TextTTS

    return TextTTS()
