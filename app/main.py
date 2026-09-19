"""FastAPI entrypoint — voice-turn API + a browser console.

Run:  uvicorn app.main:app --reload --port 8090
Then open http://localhost:8090/
"""
from __future__ import annotations

from pathlib import Path

import json

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.booking import get_booking_store
from app.dialogue.manager import DialogueManager
from app.pipeline import VoicePipeline
from app.state import SessionStore

app = FastAPI(title="voxbridge", version="0.1.0")
# Persist bookings if VOXBRIDGE_DB is set (else in-memory) — same interface either way.
pipeline = VoicePipeline(DialogueManager(get_booking_store()))
sessions = SessionStore()

CONSOLE = Path(__file__).parent / "ui" / "console.html"


class TurnRequest(BaseModel):
    text: str
    session_id: str = "default"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "stt": pipeline.stt.backend, "tts": pipeline.tts.backend}


@app.post("/v1/turns")
def turn(req: TurnRequest) -> dict:
    state = sessions.get(req.session_id)
    result, new_state = pipeline.run_turn(req.text, state)
    sessions.set(req.session_id, new_state)
    if new_state.stage in ("done", "cancelled"):
        sessions.reset(req.session_id)  # start fresh after a completed call
    return {
        "transcript": result.transcript,
        "reply": result.reply,
        "stage": result.stage,
        "booking_ref": result.booking_ref,
        "trace": result.trace,
        "total_ms": result.total_ms,
        "receipt": result.receipt,
    }


@app.post("/v1/turns/stream")
def turn_stream(req: TurnRequest) -> StreamingResponse:
    """Server-sent events: interim transcripts, then the final turn."""
    state = sessions.get(req.session_id)

    def events():
        final_state = state
        for ev in pipeline.run_turn_stream(req.text, state):
            if ev["type"] == "partial":
                payload = {"type": "partial", "text": ev["text"], "intent": ev["intent"]}
            else:
                r = ev["result"]
                final_state = ev["state"]
                payload = {"type": "final", "reply": r.reply, "stage": r.stage,
                           "booking_ref": r.booking_ref, "receipt": r.receipt,
                           "total_ms": r.total_ms, "trace": r.trace, "early": ev["early"]}
            yield f"data: {json.dumps(payload)}\n\n"
        sessions.set(req.session_id, final_state)
        if final_state.stage in ("done", "cancelled"):
            sessions.reset(req.session_id)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def console() -> str:
    return CONSOLE.read_text()
