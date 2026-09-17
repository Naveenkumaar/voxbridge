"""Microphone capture (optional).

Recording needs the optional ``sounddevice`` + ``numpy`` deps and real audio
hardware, so it lives behind a lazy import. The pure ``is_silent`` helper has no
dependencies and is unit-tested.
"""
from .barge import chunk_text, speak_interruptible
from .mic import is_silent, record_wav

__all__ = ["record_wav", "is_silent", "speak_interruptible", "chunk_text"]
