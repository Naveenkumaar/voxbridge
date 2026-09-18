"""The voice agent autonomously routes between FAQ answers and booking."""
from app.dialogue.manager import DialogueManager
from app.dialogue.nlu import detect_intent
from app.pipeline import VoicePipeline


def test_faq_vs_booking_intents():
    assert detect_intent("what are your opening hours") == "faq"
    assert detect_intent("where are you located") == "faq"
    assert detect_intent("book a table for two") == "book_table"


def test_faq_answers():
    p = VoicePipeline(DialogueManager())
    hours, _ = p.run_turn("what time do you open?", None)
    assert "12pm to 11pm" in hours.reply
    loc, _ = p.run_turn("where are you located?", None)
    assert "Riverside Walk" in loc.reply


def test_faq_mid_booking_keeps_state():
    p = VoicePipeline(DialogueManager())
    state = None
    for t in ["book a table", "tomorrow"]:
        _, state = p.run_turn(t, state)
    # ask a question mid-booking — should answer without losing progress
    ans, state = p.run_turn("by the way, is there parking?", state)
    assert "parking" in ans.reply.lower()
    assert state.slots.get("date") == "tomorrow"        # booking progress preserved
    # continue the booking
    result, state = p.run_turn("7pm", state)
    assert "How many people" in result.reply


def test_booking_still_completes_after_routing_added():
    p = VoicePipeline(DialogueManager())
    state = None
    for t in ["book a table", "tomorrow", "7pm", "2 people", "name is Ana", "yes"]:
        result, state = p.run_turn(t, state)
    assert state.stage == "done" and state.booking_ref
