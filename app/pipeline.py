"""The cascaded voice pipeline: STT -> dialogue -> TTS.

    audio/text  ─►  STT  ─►  DialogueManager  ─►  TTS  ─►  spoken reply
                    │            │                  │
                transcript   next state +        words to
                             booking action      synthesize

Each stage is pluggable (see ``stt/`` and ``tts/``) and every turn produces a
``trace`` so latency and decisions are visible end to end. The default backends
are offline stubs, so the whole cascade runs with no models and no network.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.dialogue.manager import DialogueManager, DialogueState
from app.stt import get_stt
from app.tts import get_tts


@dataclass
class TurnResult:
    transcript: str
    reply: str
    stage: str
    booking_ref: str | None
    audio_path: str | None
    trace: list[dict[str, Any]] = field(default_factory=list)
    total_ms: float = 0.0


class VoicePipeline:
    def __init__(self, manager: DialogueManager | None = None) -> None:
        self.stt = get_stt()
        self.tts = get_tts()
        self.manager = manager or DialogueManager()

    def run_turn(self, audio_or_text, state: DialogueState | None = None) -> tuple[TurnResult, DialogueState]:
        trace: list[dict[str, Any]] = []
        last = [time.perf_counter()]   # per-stage timer; ms = time since previous stage

        def timed(stage: str, **detail: Any) -> None:
            now = time.perf_counter()
            trace.append({"stage": stage, "ms": round((now - last[0]) * 1000, 2), **detail})
            last[0] = now

        # 1. STT
        transcript = self.stt.transcribe(audio_or_text)
        timed("stt", backend=transcript.backend, text=transcript.text)

        # 2. dialogue
        reply = self.manager.handle(transcript.text, state)
        timed("dialogue", slots=dict(reply.state.slots),
              next_stage=reply.state.stage, missing=reply.state.missing())

        # 3. TTS
        speech = self.tts.synthesize(reply.text)
        timed("tts", backend=speech.backend, audio=bool(speech.audio_path))

        result = TurnResult(
            transcript=transcript.text,
            reply=reply.text,
            stage=reply.state.stage,
            booking_ref=reply.state.booking_ref,
            audio_path=speech.audio_path,
            trace=trace,
            total_ms=round(sum(s["ms"] for s in trace), 2),
        )
        return result, reply.state
