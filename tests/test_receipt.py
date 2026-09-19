"""A completed booking emits a structured, machine-readable receipt."""
from app.dialogue.manager import DialogueManager
from app.pipeline import VoicePipeline


def _book(pipeline, turns):
    state = None
    result = None
    for t in turns:
        result, state = pipeline.run_turn(t, state)
    return result, state


def test_receipt_is_populated_on_confirmation():
    p = VoicePipeline(DialogueManager())
    result, _ = _book(p, ["book a table for 2 tomorrow at 7pm, name is Sam",
                          "window seat", "yes"])
    r = result.receipt
    assert r is not None
    assert r["status"] == "confirmed"
    assert r["confirmation"] == result.booking_ref
    assert r["party_size"] == "2" and r["date"] == "tomorrow" and r["time"] == "7:00 pm"
    assert r["name"] == "Sam"
    assert r["special_request"] == "window seat"


def test_no_receipt_before_confirmation():
    p = VoicePipeline(DialogueManager())
    result, _ = p.run_turn("book a table for 2 tomorrow at 7pm, name is Sam", None)
    assert result.receipt is None          # still confirming, not booked


def test_receipt_omits_absent_optional_fields():
    p = VoicePipeline(DialogueManager())
    result, _ = _book(p, ["table for 3 friday at 8pm, name is Ana", "yes"])
    assert "special_request" not in result.receipt   # none given → not in the record


def test_api_returns_the_receipt():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    sid = "receipt-test"
    for t in ["book a table for 2 tomorrow at 7pm, name is Sam", "yes"]:
        data = client.post("/v1/turns", json={"text": t, "session_id": sid}).json()
    assert data["receipt"]["confirmation"] == data["booking_ref"]
    assert data["receipt"]["status"] == "confirmed"
