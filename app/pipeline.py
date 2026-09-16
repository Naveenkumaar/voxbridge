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


class VoicePipeline:
    def __init__(self, manager: DialogueManager | None = None) -> None:
        self.stt = get_stt()
        self.tts = get_tts()
        self.manager = manager or DialogueManager()

    def run_turn(self, audio_or_text, state: DialogueState | None = None) -> tuple[TurnResult, DialogueState]:
        trace: list[dict[str, Any]] = []

        # 1. STT
        transcript = self.stt.transcribe(audio_or_text)
        trace.append({"stage": "stt", "backend": transcript.backend, "text": transcript.text})

        # 2. dialogue
        reply = self.manager.handle(transcript.text, state)
        trace.append({
            "stage": "dialogue",
            "slots": dict(reply.state.slots),
            "next_stage": reply.state.stage,
            "missing": reply.state.missing(),
        })

        # 3. TTS
        speech = self.tts.synthesize(reply.text)
        trace.append({"stage": "tts", "backend": speech.backend, "audio": bool(speech.audio_path)})

        result = TurnResult(
            transcript=transcript.text,
            reply=reply.text,
            stage=reply.state.stage,
            booking_ref=reply.state.booking_ref,
            audio_path=speech.audio_path,
            trace=trace,
        )
        return result, reply.state
