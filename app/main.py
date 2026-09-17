"""FastAPI entrypoint — voice-turn API + a browser console.

Run:  uvicorn app.main:app --reload --port 8090
Then open http://localhost:8090/
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
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
    }


@app.get("/", response_class=HTMLResponse)
def console() -> str:
    return CONSOLE.read_text()
