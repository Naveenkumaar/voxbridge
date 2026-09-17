"""Tests for lookup, modify, and special-request handling."""
from app.dialogue.manager import DialogueManager
from app.dialogue.nlu import detect_intent, extract_slots
from app.pipeline import VoicePipeline


def _book(pipeline, extra=""):
    state = None
    for t in ["book a table", "tomorrow", "7pm", "4 people", "name is Naveen" + extra, "yes"]:
        _, state = pipeline.run_turn(t, state)
    return state


def test_new_intents_detected():
    assert detect_intent("look up my booking VB-0001") == "lookup"
    assert detect_intent("can we change the time") == "modify"
    assert detect_intent("book a table") == "book_table"   # still wins for a real booking


def test_ref_and_special_request_extraction():
    assert extract_slots("my ref is VB-12")["ref"] == "VB-0012"
    assert extract_slots("a window seat please")["special_request"] == "window seat"


def test_lookup_after_booking_returns_details():
    m = DialogueManager()
    pipeline = VoicePipeline(m)
    state = _book(pipeline)
    ref = state.booking_ref
    result, _ = pipeline.run_turn(f"can you look up {ref}?", state)
    assert ref in result.reply and "Naveen" in result.reply


def test_lookup_unknown_ref():
    result, _ = VoicePipeline(DialogueManager()).run_turn("look up booking VB-9999", None)
    assert "couldn't find" in result.reply.lower()


def test_modify_reconfirms_with_new_value():
    m = DialogueManager()
    pipeline = VoicePipeline(m)
    # complete a booking up to confirmation
    state = None
    for t in ["book a table", "tomorrow", "7pm", "4 people", "name is Sam"]:
        _, state = pipeline.run_turn(t, state)
    assert state.stage == "confirming"
    result, state = pipeline.run_turn("actually change it to 9pm", state)
    assert state.stage == "confirming"
    assert "9:00 pm" in result.reply          # new time folded in and re-confirmed


def test_special_request_appears_in_confirmation():
    m = DialogueManager()
    pipeline = VoicePipeline(m)
    state = None
    for t in ["book a table for 2 tomorrow at 8pm, name is Ana", "a window seat"]:
        result, state = pipeline.run_turn(t, state)
    assert "window seat" in result.reply
