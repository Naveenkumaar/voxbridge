"""Streaming partial transcripts + early-stop on a terminal intent."""
import json

from app.dialogue.manager import DialogueManager
from app.pipeline import VoicePipeline
from app.stt.stub import TextSTT


def test_stt_stream_emits_growing_prefixes_then_final():
    chunks = list(TextSTT().stream("book a table please"))
    assert [c.text for c in chunks] == [
        "book", "book a", "book a table", "book a table please"]
    assert all(c.partial for c in chunks[:-1])
    assert chunks[-1].partial is False


def test_pipeline_stream_yields_partials_then_final():
    p = VoicePipeline(DialogueManager())
    events = list(p.run_turn_stream("book a table for 2", None))
    partials = [e for e in events if e["type"] == "partial"]
    finals = [e for e in events if e["type"] == "final"]
    assert partials and len(finals) == 1
    assert partials[0]["text"] == "book"           # first interim result
    assert finals[0]["result"].transcript == "book a table for 2"
    assert finals[0]["early"] is False


def test_early_stop_on_cancel_midway():
    p = VoicePipeline(DialogueManager())
    events = list(p.run_turn_stream("actually cancel the whole thing", None))
    final = [e for e in events if e["type"] == "final"][0]
    assert final["early"] is True                   # settled before the full utterance
    assert final["state"].stage == "cancelled"
    # it acted on a prefix, not the whole sentence
    assert final["result"].transcript == "actually cancel"


def test_sse_endpoint_streams_events():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    body = client.post("/v1/turns/stream",
                       json={"text": "book a table for 2", "session_id": "stream-test"}).text
    events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]
    assert any(e["type"] == "partial" for e in events)
    final = [e for e in events if e["type"] == "final"][0]
    assert "reply" in final and "total_ms" in final
