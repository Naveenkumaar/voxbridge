"""Barge-in — stop speaking the moment the user starts talking.

The core is pure and testable: ``speak_interruptible`` emits the reply chunk by
chunk and halts as soon as an ``should_interrupt()`` signal goes true, returning
what was actually spoken. In a live setup that signal is "the mic heard speech"
(voice activity); here it's any callable, so the logic is unit-tested without
audio.
"""
from __future__ import annotations

from typing import Callable, Iterable


def chunk_text(text: str) -> list[str]:
    """Split a reply into speakable chunks (word tokens with trailing spaces)."""
    words = text.split(" ")
    return [(w if i == 0 else " " + w) for i, w in enumerate(words) if w != "" or i == 0]


def speak_interruptible(
    chunks: Iterable[str],
    should_interrupt: Callable[[], bool],
    on_chunk: Callable[[str], None] | None = None,
) -> tuple[str, bool]:
    """Speak ``chunks`` one at a time, checking ``should_interrupt()`` *before*
    each. Stop early if it returns True.

    Returns ``(spoken_text, interrupted)`` — ``spoken_text`` is what actually
    made it out before the barge-in (empty string if cut off at the very start).
    """
    spoken: list[str] = []
    for chunk in chunks:
        if should_interrupt():
            return "".join(spoken), True
        spoken.append(chunk)
        if on_chunk:
            on_chunk(chunk)
    return "".join(spoken), False
