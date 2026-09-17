"""Live microphone capture → WAV, for the cascaded pipeline's STT stage.

``record_wav`` records from the default input device and writes a 16-bit mono
WAV (the format faster-whisper reads). It needs ``sounddevice`` + ``numpy`` and a
real mic, so those imports are lazy. ``is_silent`` is pure Python (no deps) so
the capture loop can trim silence and stop on quiet — and it's unit-testable.
"""
from __future__ import annotations

import tempfile
import wave


def record_wav(seconds: float = 5.0, samplerate: int = 16000) -> str:
    """Record ``seconds`` of mono audio from the default mic; return a WAV path."""
    import sounddevice as sd  # optional dep

    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate,
                   channels=1, dtype="int16")
    sd.wait()
    path = tempfile.mktemp(suffix=".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)          # int16
        w.setframerate(samplerate)
        w.writeframes(audio.tobytes())
    return path


def is_silent(samples, threshold: float = 500.0) -> bool:
    """True if the mean absolute amplitude is below ``threshold``.

    Pure Python — accepts any iterable of int samples. Used to trim silence and
    to stop the listen loop after quiet.
    """
    samples = list(samples)
    if not samples:
        return True
    return (sum(abs(int(s)) for s in samples) / len(samples)) < threshold
