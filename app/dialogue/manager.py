"""Slot-filling dialogue manager.

Owns the conversation policy: track which booking slots are still missing, ask
for the next one, confirm, then commit — plus look up and modify existing
bookings. Pure and deterministic — given a state and an utterance it returns the
next state and the words to speak, so the whole conversation is testable without
audio or an LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.booking import BookingStore
from app.dialogue.nlu_router import detect_intent, extract_slots

REQUIRED = ["date", "time", "party_size", "name"]   # 'special_request' is optional

# Small FAQ capability — the agent autonomously answers these instead of booking.
_FAQ = {
    "hours": ("hour", "open", "opening", "closing", "timing"),
    "location": ("where", "located", "location", "address"),
    "parking": ("parking", "car park"),
    "contact": ("phone", "contact", "number"),
    "menu": ("menu", "dress code"),
}
_FAQ_ANSWERS = {
    "hours": "We're open every day from 12pm to 11pm.",
    "location": "We're at 12 Riverside Walk, just past the old bridge.",
    "parking": "There's street parking nearby and a car park two minutes away.",
    "contact": "You can reach us on 555-0100.",
    "menu": "Smart-casual is fine, and the menu's on our website.",
}

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
    receipt: dict | None = None   # structured record, set once a booking is confirmed

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

        heard = extract_slots(text)
        ref = heard.pop("ref", None)

        # cancel/modify an existing booking by reference (post-confirmation)
        if intent == "cancel" and ref:
            return self._cancel_ref(ref, state)
        if intent == "cancel":
            state.stage = "cancelled"
            return Reply("No problem — I've cancelled that. Anything else?", state)
        if intent == "modify" and ref:
            return self._modify_ref(ref, heard, state)

        if intent == "list" and not ref:
            return self._list(state)
        if intent == "lookup" or ref:                 # a reference always means "look it up"
            return self._lookup(ref or state.booking_ref, state)
        if intent == "faq":                           # answer a general question, keep booking state
            return self._faq(text, state)

        # After a finished booking, a new request starts a fresh one (store persists).
        if state.stage in ("done", "cancelled"):
            state = DialogueState()

        # Fold any booking slots we heard, at any stage.
        state.slots.update(heard)

        if intent == "modify":
            return self._modify(state)

        if state.stage == "confirming":
            # New info at confirmation (not a yes/no) → fold it in and re-confirm.
            if intent not in ("affirm", "deny") and heard:
                return self._modify(state)
            return self._confirm(intent, state)

        if intent == "greet" and not state.slots:
            return Reply("Hi! I can book you a table. " + _PROMPTS["date"], state)

        return self._collect(state)

    # ------------------------------------------------------------------
    def _confirm_text(self, state: DialogueState) -> str:
        s = state.slots
        extra = f", {s['special_request']}" if s.get("special_request") else ""
        return (f"Let me confirm: a table for {s['party_size']} under {s['name']}, "
                f"{s['date']} at {s['time']}{extra}. Shall I book it?")

    def _collect(self, state: DialogueState) -> Reply:
        missing = state.missing()
        if missing:
            return Reply(_PROMPTS[missing[0]], state)
        state.stage = "confirming"
        return Reply(self._confirm_text(state), state)

    def _confirm(self, intent: str, state: DialogueState) -> Reply:
        if intent == "deny":
            state.stage = "collecting"
            return Reply("Okay, what should I change?", state)
        if intent == "affirm":
            ref = self.store.create(state.slots)
            state.stage = "done"
            state.booking_ref = ref
            state.receipt = self._receipt(ref, state.slots)
            s = state.slots
            extra = f", {s['special_request']}" if s.get("special_request") else ""
            return Reply(
                f"Booked! Table for {s['party_size']}, {s['date']} at {s['time']}{extra}. "
                f"Your confirmation is {ref}. See you then!",
                state,
            )
        return Reply("Sorry, was that a yes or a no?", state)

    @staticmethod
    def _receipt(ref: str, slots: dict[str, str]) -> dict:
        """A structured, machine-readable record of the confirmed booking.

        A downstream system (email/SMS/CRM) consumes this instead of parsing the
        spoken reply. Only the fields that exist are included.
        """
        receipt = {
            "confirmation": ref,
            "status": "confirmed",
            "party_size": slots.get("party_size"),
            "date": slots.get("date"),
            "time": slots.get("time"),
            "name": slots.get("name"),
        }
        if slots.get("special_request"):
            receipt["special_request"] = slots["special_request"]
        return {k: v for k, v in receipt.items() if v is not None}

    def _modify(self, state: DialogueState) -> Reply:
        """User wants to change something (a slot was likely just folded in).
        Re-confirm if the booking is complete, else ask for what's still missing.
        """
        missing = state.missing()
        if missing:
            state.stage = "collecting"
            return Reply("Sure — " + _PROMPTS[missing[0]], state)
        state.stage = "confirming"
        return Reply("Sure, I've updated that. " + self._confirm_text(state), state)

    def _modify_ref(self, ref: str, changes: dict[str, str], state: DialogueState) -> Reply:
        """Change a stored booking identified by its reference (out of band)."""
        b = self.store.get(ref)
        if b is None or b.get("status") == "cancelled":
            return Reply(f"I couldn't find an active booking under {ref}.", state)
        if not changes:
            return Reply(f"Sure — what would you like to change about {ref}?", state)
        self.store.update(ref, changes)
        summary = ", ".join(f"{k.replace('_', ' ')} to {v}" for k, v in changes.items())
        return Reply(f"Done — I've updated {ref}: {summary}.", state)

    def _cancel_ref(self, ref: str, state: DialogueState) -> Reply:
        """Cancel a stored booking identified by its reference."""
        if self.store.cancel(ref):
            return Reply(f"Done — booking {ref} is cancelled. Anything else?", state)
        return Reply(f"I couldn't find a booking under {ref}.", state)

    def _faq(self, text: str, state: DialogueState) -> Reply:
        low = text.lower()
        for topic, keywords in _FAQ.items():
            if any(k in low for k in keywords):
                return Reply(_FAQ_ANSWERS[topic], state)
        return Reply("I can help with bookings, hours, location, and parking — "
                     "what would you like?", state)

    def _list(self, state: DialogueState) -> Reply:
        bookings = self.store.all()
        if not bookings:
            return Reply("You don't have any bookings yet.", state)
        parts = [f"{ref} — {b['party_size']} on {b['date']} at {b['time']} ({b['name']})"
                 for ref, b in bookings.items()]
        return Reply("Your bookings: " + "; ".join(parts) + ".", state)

    def _lookup(self, ref: str | None, state: DialogueState) -> Reply:
        if not ref:
            return Reply("Sure — what's your booking reference? It looks like VB-0001.", state)
        b = self.store.get(ref)
        if not b:
            return Reply(f"I couldn't find a booking under {ref}.", state)
        if b.get("status") == "cancelled":
            return Reply(f"Booking {ref} was cancelled.", state)
        extra = f", {b['special_request']}" if b.get("special_request") else ""
        return Reply(
            f"Found {ref}: a table for {b['party_size']} under {b['name']}, "
            f"{b['date']} at {b['time']}{extra}.",
            state,
        )
