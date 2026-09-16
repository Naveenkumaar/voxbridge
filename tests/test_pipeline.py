from app.dialogue.manager import DialogueManager
from app.pipeline import VoicePipeline


def _run(pipeline, utterances):
    state = None
    result = None
    for text in utterances:
        result, state = pipeline.run_turn(text, state)
    return result, state


def test_full_booking_flow_reaches_confirmation_and_books():
    pipeline = VoicePipeline(DialogueManager())
    result, state = _run(pipeline, [
        "hi",
        "book a table",
        "tomorrow",
        "7pm",
        "4 people",
        "the name is Naveen",
        "yes",
    ])
    assert state.stage == "done"
    assert result.booking_ref and result.booking_ref.startswith("VB-")
    assert "Booked" in result.reply


def test_single_utterance_fills_all_slots():
    pipeline = VoicePipeline(DialogueManager())
    result, state = _run(pipeline, [
        "book a table for 2 tomorrow at 8pm, name is Sam",
    ])
    # everything heard at once -> straight to confirmation
    assert state.stage == "confirming"
    assert "confirm" in result.reply.lower()


def test_cancel_midway():
    pipeline = VoicePipeline(DialogueManager())
    result, state = _run(pipeline, ["book a table", "actually cancel"])
    assert state.stage == "cancelled"


def test_trace_has_all_three_stages():
    pipeline = VoicePipeline(DialogueManager())
    result, _ = _run(pipeline, ["hi"])
    stages = [s["stage"] for s in result.trace]
    assert stages == ["stt", "dialogue", "tts"]


def test_deny_then_correct():
    pipeline = VoicePipeline(DialogueManager())
    result, state = _run(pipeline, [
        "book for 2 tomorrow at 6pm name Ana",
        "no",
    ])
    assert state.stage == "collecting"
