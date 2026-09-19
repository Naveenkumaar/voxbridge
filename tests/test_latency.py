"""Every turn is instrumented with per-stage latency and an end-to-end total."""
from app.dialogue.manager import DialogueManager
from app.pipeline import VoicePipeline


def test_every_stage_has_a_millisecond_reading():
    p = VoicePipeline(DialogueManager())
    result, _ = p.run_turn("book a table for 2 tomorrow at 7pm, name is Sam", None)
    stages = [s["stage"] for s in result.trace]
    assert stages == ["stt", "dialogue", "tts"]
    for s in result.trace:
        assert "ms" in s and isinstance(s["ms"], (int, float)) and s["ms"] >= 0


def test_total_ms_is_the_sum_of_stage_ms():
    p = VoicePipeline(DialogueManager())
    result, _ = p.run_turn("hi", None)
    assert result.total_ms == round(sum(s["ms"] for s in result.trace), 2)
    assert result.total_ms >= 0


def test_api_response_includes_total_ms():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    data = client.post("/v1/turns", json={"text": "hi", "session_id": "lat-test"}).json()
    assert "total_ms" in data
    assert all("ms" in s for s in data["trace"])
