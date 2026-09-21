#!/usr/bin/env python3
"""One-command, offline end-to-end demo of the cascaded voice agent.

    python scripts/demo.py

Runs on the text stubs (no audio models, no network). Walks through: autonomous
FAQ-vs-booking routing, a full slot-filling booking with a structured receipt,
streaming partial transcripts + reply chunks (with early-stop on "cancel"), and
modifying / cancelling a stored booking by reference.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.booking.store import BookingStore  # noqa: E402
from app.dialogue.manager import DialogueManager  # noqa: E402
from app.pipeline import VoicePipeline  # noqa: E402


def rule(title: str) -> None:
    print(f"\n\033[1m{'─' * 3} {title} {'─' * (60 - len(title))}\033[0m")


def say(pipeline, state, text):
    result, state = pipeline.run_turn(text, state)
    print(f"  you › {text}")
    print(f"  bot › {result.reply}  \033[90m[{result.total_ms} ms]\033[0m")
    return result, state


def main() -> int:
    pipeline = VoicePipeline(DialogueManager(BookingStore()))

    rule("Autonomous routing: FAQ vs booking")
    say(pipeline, None, "what are your opening hours?")           # answered as FAQ
    say(pipeline, None, "where are you located?")

    rule("A full booking (slot-filling → confirm → receipt)")
    state = None
    for turn in ["book a table for 2 tomorrow at half past 7",
                 "name is Sam", "a window seat", "yes"]:
        result, state = say(pipeline, state, turn)
    print(f"\n  🧾 receipt: {result.receipt}")
    ref = result.booking_ref

    rule("Question mid-booking keeps progress")
    state = None
    _, state = say(pipeline, state, "book a table")
    _, state = say(pipeline, state, "tomorrow")
    _, state = say(pipeline, state, "by the way is there parking?")
    print(f"  (booking progress preserved: date={state.slots.get('date')!r})")

    rule("Streaming: partial transcripts in, reply chunks out")
    events = list(pipeline.run_turn_stream("book a table for four on friday at 8pm", None))
    partials = [e["text"] for e in events if e["type"] == "partial"]
    chunks = [e["text"] for e in events if e["type"] == "reply_chunk"]
    print(f"  partial transcripts: {partials[:3]} … ({len(partials)} interim)")
    print(f"  reply chunks:        {chunks}")

    rule("Streaming early-stop on a terminal intent")
    ev = list(pipeline.run_turn_stream("actually cancel this whole thing", None))
    final = [e for e in ev if e["type"] == "final"][0]
    print(f"  settled early on partial: {final['result'].transcript!r} → "
          f"stage={final['state'].stage}")

    rule("Modify / cancel a stored booking by reference")
    say(pipeline, None, f"change booking {ref} to 9pm")
    say(pipeline, None, f"look up {ref}")
    say(pipeline, None, f"cancel booking {ref}")
    say(pipeline, None, f"look up {ref}")

    rule("Done")
    print("Everything above ran offline on text stubs. Set "
          "STT_BACKEND=whisper / TTS_BACKEND=pyttsx3 / NLU_BACKEND=llm for real backends.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
