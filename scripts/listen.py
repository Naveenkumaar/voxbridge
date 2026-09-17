"""Live voice loop — talk to voxbridge through your microphone.

    STT_BACKEND=whisper TTS_BACKEND=pyttsx3 python scripts/listen.py

Each round: record from the mic → transcribe (faster-whisper) → run the
cascaded pipeline → speak/print the reply. Say "quit" (or stay silent twice) to
stop. Needs the optional deps:  pip install -r requirements-optional.txt

With no mic/deps this exits with a clear message — the offline text demo is
``scripts/talk.py``.
"""
from __future__ import annotations

import os
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.audio import chunk_text, is_silent, record_wav, speak_interruptible  # noqa: E402
from app.pipeline import VoicePipeline  # noqa: E402


def _mic_has_voice() -> bool:
    """Barge-in signal: did the mic just hear speech? Best-effort — needs real
    duplex audio; returns False if capture isn't available so speech isn't cut off."""
    try:
        return not is_silent(_wav_samples(record_wav(seconds=0.4)))
    except Exception:
        return False


def _wav_samples(path: str) -> list[int]:
    with wave.open(path, "rb") as w:
        import array
        a = array.array("h")
        a.frombytes(w.readframes(w.getnframes()))
        return list(a)


def main() -> int:
    if os.getenv("STT_BACKEND", "text").lower() != "whisper":
        print("Set STT_BACKEND=whisper (and ideally TTS_BACKEND=pyttsx3) to use the mic.")
        print("For the offline text demo, run scripts/talk.py instead.")
        return 1

    pipeline = VoicePipeline()
    state = None
    quiet = 0
    print("voxbridge — listening. Speak after each prompt; say 'quit' to stop.\n")
    while True:
        input("↵ press Enter, then speak… ")
        try:
            wav = record_wav(seconds=5)
        except Exception as exc:  # no mic / deps missing
            print(f"Could not record ({exc}). Install requirements-optional.txt and check your mic.")
            return 1

        if is_silent(_wav_samples(wav)):
            quiet += 1
            print("(heard nothing)")
            if quiet >= 2:
                print("Goodbye."); break
            continue
        quiet = 0

        result, state = pipeline.run_turn(wav, state)   # STT → dialogue → TTS
        print(f"you › {result.transcript}")
        # speak the reply, but stop the moment the caller starts talking (barge-in)
        spoken, interrupted = speak_interruptible(
            chunk_text(result.reply), _mic_has_voice, on_chunk=lambda c: print(c, end="", flush=True))
        print()
        if interrupted:
            print("(interrupted — listening…)")
            continue
        print(f"bot › {result.reply}")
        if result.transcript.strip().lower() in {"quit", "exit", "stop"}:
            break
        if result.stage in ("done", "cancelled"):
            print(f"      [{result.stage}"
                  + (f" · {result.booking_ref}]" if result.booking_ref else "]"))
            state = None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
