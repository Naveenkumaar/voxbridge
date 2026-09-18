"""List intent + multiple bookings in one session."""
from app.dialogue.manager import DialogueManager
from app.dialogue.nlu import detect_intent
from app.pipeline import VoicePipeline


def _book(pipeline, state, name):
    for t in ["book a table", "tomorrow", "7pm", "3 people", f"name is {name}", "yes"]:
        _, state = pipeline.run_turn(t, state)
    return state


def test_list_intent_detected_and_ref_wins():
    assert detect_intent("show me all my bookings") == "list"
    assert detect_intent("look up booking VB-0001") == "lookup"


def test_list_when_empty():
    result, _ = VoicePipeline(DialogueManager()).run_turn("show my bookings", None)
    assert "don't have any bookings" in result.reply.lower()


def test_two_bookings_in_one_session():
    m = DialogueManager()
    pipeline = VoicePipeline(m)
    state = _book(pipeline, None, "Naveen")
    assert state.stage == "done"
    first = state.booking_ref
    # a new request after a finished booking starts fresh
    state = _book(pipeline, state, "Sam")
    assert state.stage == "done"
    assert state.booking_ref != first
    assert len(m.store.all()) == 2


def test_list_shows_all_bookings():
    m = DialogueManager()
    pipeline = VoicePipeline(m)
    state = _book(pipeline, None, "Ana")
    state = _book(pipeline, state, "Bo")
    result, _ = pipeline.run_turn("list my bookings", state)
    assert "Ana" in result.reply and "Bo" in result.reply
    assert result.reply.count("VB-") == 2


def test_ref_lookup_not_treated_as_list():
    m = DialogueManager()
    pipeline = VoicePipeline(m)
    state = _book(pipeline, None, "Ivy")
    ref = state.booking_ref
    result, _ = pipeline.run_turn(f"show my booking {ref}", state)
    assert ref in result.reply and "Ivy" in result.reply and ";" not in result.reply
