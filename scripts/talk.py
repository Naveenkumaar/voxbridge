"""Interactive CLI — hold a full booking conversation in the terminal.

    python scripts/talk.py

Type what you'd say to the agent; it runs the same STT->dialogue->TTS pipeline
the API uses (text stubs by default, so no audio hardware needed).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.pipeline import VoicePipeline  # noqa: E402


def main() -> int:
    pipeline = VoicePipeline()
    state = None
    print("voxbridge — table booking. Say hello (or 'quit').\n")
    while True:
        try:
            text = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"quit", "exit"}:
            break
        result, state = pipeline.run_turn(text, state)
        print(f"bot › {result.reply}")
        if result.stage in ("done", "cancelled"):
            print(f"      [{result.stage}"
                  + (f" · {result.booking_ref}]" if result.booking_ref else "]"))
            state = None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
