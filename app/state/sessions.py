"""Keeps a DialogueState per session id so multi-turn calls stay coherent."""
from __future__ import annotations

from app.dialogue.manager import DialogueState


class SessionStore:
    def __init__(self) -> None:
        self._states: dict[str, DialogueState] = {}

    def get(self, session_id: str) -> DialogueState:
        return self._states.setdefault(session_id, DialogueState())

    def set(self, session_id: str, state: DialogueState) -> None:
        self._states[session_id] = state

    def reset(self, session_id: str) -> None:
        self._states.pop(session_id, None)
