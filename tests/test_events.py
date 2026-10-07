"""Each voice turn emits a normalized event stream for the live timeline."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.events import EventBus, EventType, bus
from app.main import app

client = TestClient(app)


def test_bus_ring_buffer_and_since_seq():
    b = EventBus(maxlen=4)
    for i in range(6):
        b.emit("r1", EventType.STAGE, stage="stt", i=i)
    recent = b.recent()
    assert len(recent) == 4
    seqs = [e["seq"] for e in recent]
    assert seqs == sorted(seqs)
    assert [e["seq"] for e in b.recent(since_seq=seqs[-1])] == []


def test_turn_emits_started_stages_completed():
    bus.clear()
    r = client.post("/v1/turns", json={"text": "I'd like to book a table", "session_id": "t1"})
    assert r.status_code == 200
    assert r.json().get("run_id")

    types = [e["type"] for e in client.get("/events").json()["events"]]
    assert types[0] == "run.started"
    assert "run.stage" in types
    assert types[-1] == "run.completed"

    runs = client.get("/events/runs").json()["runs"]
    assert runs and runs[0]["status"] == "run.completed"
    stages = [e["stage"] for e in runs[0]["events"] if e["type"] == "run.stage"]
    assert stages == ["stt", "dialogue", "tts"]   # the cascade, in order
