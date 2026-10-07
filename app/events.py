"""A normalized, in-process event stream for voice turns.

Each turn emits one ``run.started``, one ``run.stage`` per pipeline stage
(stt → dialogue → tts), and one ``run.completed`` / ``run.failed``. It is the data
behind the console's live **turn timeline**: a safe, structured view of what the
pipeline is doing and how long each stage takes — never the model's hidden reasoning.

Dependency-free and in-process: a bounded ring buffer plus optional subscribers.
Emission is best-effort — a failing subscriber can never break a turn.
"""
from __future__ import annotations

import itertools
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class EventType(str, Enum):
    RUN_STARTED = "run.started"
    STAGE = "run.stage"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"


TERMINAL = {EventType.RUN_COMPLETED, EventType.RUN_FAILED}


@dataclass
class TurnEvent:
    seq: int
    ts: float
    run_id: str
    type: EventType
    stage: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "ts": self.ts, "run_id": self.run_id,
                "type": self.type.value, "stage": self.stage, "detail": self.detail}


class EventBus:
    def __init__(self, maxlen: int = 2000) -> None:
        self._events: deque[TurnEvent] = deque(maxlen=maxlen)
        self._seq = itertools.count(1)
        self._subscribers: list[Callable[[TurnEvent], None]] = []

    def subscribe(self, fn: Callable[[TurnEvent], None]) -> None:
        self._subscribers.append(fn)

    def emit(self, run_id: str, type: EventType, stage: str | None = None,
             **detail: Any) -> TurnEvent:
        ev = TurnEvent(seq=next(self._seq), ts=time.time(), run_id=run_id,
                       type=type, stage=stage, detail=detail)
        self._events.append(ev)
        for fn in list(self._subscribers):
            try:
                fn(ev)
            except Exception:  # noqa: BLE001 — a subscriber must never break a turn
                pass
        return ev

    def recent(self, limit: int = 200, since_seq: int = 0) -> list[dict[str, Any]]:
        out = [e.to_dict() for e in self._events if e.seq > since_seq]
        return out[-limit:]

    def runs(self, limit: int = 25) -> list[dict[str, Any]]:
        by_run: dict[str, dict[str, Any]] = {}
        for e in self._events:
            g = by_run.setdefault(e.run_id, {
                "run_id": e.run_id, "events": [], "status": "running"})
            g["events"].append(e.to_dict())
            if e.type in TERMINAL:
                g["status"] = e.type.value
            g["latest"] = e.ts
        return sorted(by_run.values(), key=lambda g: g.get("latest", 0),
                      reverse=True)[:limit]

    def clear(self) -> None:
        self._events.clear()


# Process-wide bus the pipeline and API share.
bus = EventBus()
