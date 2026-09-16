"""Slot-filling dialogue manager.

Owns the conversation policy: track which booking slots are still missing, ask
for the next one, confirm, then commit. Pure and deterministic — given a state
and an utterance it returns the next state and the words to speak. That makes
the whole conversation testable without audio or an LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.booking import BookingStore
from app.dialogue.nlu import detect_intent, extract_slots

REQUIRED = ["date", "time", "party_size", "name"]

_PROMPTS = {
    "date": "What day would you like to book for?",
    "time": "What time works for you?",
    "party_size": "How many people will be dining?",
    "name": "And what name should I put the reservation under?",
}


@dataclass
class DialogueState:
    slots: dict[str, str] = field(default_factory=dict)
    stage: str = "collecting"  # collecting -> confirming -> done | cancelled
    booking_ref: str | None = None

    def missing(self) -> list[str]:
        return [s for s in REQUIRED if s not in self.slots]


@dataclass
class Reply:
    text: str
    state: DialogueState


class DialogueManager:
    def __init__(self, store: BookingStore | None = None) -> None:
        self.store = store or BookingStore()

    def handle(self, text: str, state: DialogueState | None = None) -> Reply:
        state = state or DialogueState()
        intent = detect_intent(text)

        if intent == "cancel":
            state.stage = "cancelled"
            return Reply("No problem — I've cancelled that. Anything else?", state)

        # Always fold any slots we can hear, at any stage.
        state.slots.update(extract_slots(text))

        if state.stage == "confirming":
            return self._confirm(intent, state)

        if intent == "greet" and not state.slots:
            return Reply(
                "Hi! I can book you a table. " + _PROMPTS["date"], state
            )

        return self._collect(state)

    # ------------------------------------------------------------------
    def _collect(self, state: DialogueState) -> Reply:
        missing = state.missing()
        if missing:
            return Reply(_PROMPTS[missing[0]], state)
        state.stage = "confirming"
        s = state.slots
        return Reply(
            f"Let me confirm: a table for {s['party_size']} under {s['name']}, "
            f"{s['date']} at {s['time']}. Shall I book it?",
            state,
        )

    def _confirm(self, intent: str, state: DialogueState) -> Reply:
        if intent == "deny":
            state.stage = "collecting"
            return Reply("Okay, what should I change?", state)
        if intent == "affirm":
            ref = self.store.create(state.slots)
            state.stage = "done"
            state.booking_ref = ref
            s = state.slots
            return Reply(
                f"Booked! Table for {s['party_size']}, {s['date']} at {s['time']}. "
                f"Your confirmation is {ref}. See you then!",
                state,
            )
        return Reply("Sorry, was that a yes or a no?", state)
