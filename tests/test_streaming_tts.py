"""Streaming TTS — the reply is emitted in speakable chunks."""
import json

from app.dialogue.manager import DialogueManager
from app.pipeline import VoicePipeline
from app.tts.stub import TextTTS


def test_tts_stream_chunks_by_sentence():
    chunks = [s.text for s in TextTTS().synthesize_stream("Booked! Table for 2. See you then!")]
    assert chunks == ["Booked!", "Table for 2.", "See you then!"]


def test_tts_stream_single_sentence_is_one_chunk():
    chunks = list(TextTTS().synthesize_stream("What day would you like?"))
    assert len(chunks) == 1 and chunks[0].text == "What day would you like?"


def test_pipeline_stream_emits_reply_chunks_before_final():
    p = VoicePipeline(DialogueManager())
    events = list(p.run_turn_stream("book a table for 2 tomorrow at 7pm, name is Sam", None))
    types = [e["type"] for e in events]
    # partials first, then reply chunks, then exactly one final
    assert "reply_chunk" in types
    assert types.index("reply_chunk") < types.index("final")
    assert types.count("final") == 1
    # concatenated chunks reconstruct the reply
    spoken = " ".join(e["text"] for e in events if e["type"] == "reply_chunk")
    final = [e for e in events if e["type"] == "final"][0]
    assert spoken == final["result"].reply


def test_sse_includes_reply_chunks():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    body = client.post("/v1/turns/stream",
                       json={"text": "book a table for 2", "session_id": "tts-stream"}).text
    events = [json.loads(l[6:]) for l in body.splitlines() if l.startswith("data: ")]
    assert any(e["type"] == "reply_chunk" for e in events)
    assert any(e["type"] == "final" for e in events)
