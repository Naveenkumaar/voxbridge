"""Modify or cancel an existing booking by reference (post-confirmation)."""
from app.booking.store import BookingStore
from app.dialogue.manager import DialogueManager
from app.pipeline import VoicePipeline


def _pipeline():
    return VoicePipeline(DialogueManager(BookingStore()))


def _book(p):
    state = None
    for t in ["book a table for 2 tomorrow at 7pm, name is Sam", "yes"]:
        result, state = p.run_turn(t, state)
    return result.booking_ref, state


def test_modify_existing_booking_by_reference():
    p = _pipeline()
    ref, state = _book(p)
    result, _ = p.run_turn(f"change booking {ref} to 9pm", state)
    assert ref in result.reply and "9:00 pm" in result.reply
    # the stored booking actually changed
    assert p.manager.store.get(ref)["time"] == "9:00 pm"


def test_cancel_existing_booking_by_reference():
    p = _pipeline()
    ref, state = _book(p)
    result, _ = p.run_turn(f"cancel booking {ref}", state)
    assert ref in result.reply and "cancelled" in result.reply.lower()
    assert p.manager.store.get(ref)["status"] == "cancelled"
    # a later lookup reports it as cancelled
    looked, _ = p.run_turn(f"look up {ref}", None)
    assert "cancelled" in looked.reply.lower()


def test_modify_unknown_reference():
    p = _pipeline()
    result, _ = p.run_turn("change booking VB-9999 to 9pm", None)
    assert "couldn't find" in result.reply.lower()


def test_plain_cancel_without_ref_still_cancels_current():
    p = _pipeline()
    _, state = p.run_turn("book a table for 2", None)
    result, state = p.run_turn("cancel", state)
    assert state.stage == "cancelled"


def test_store_update_and_cancel_directly():
    s = BookingStore()
    ref = s.create({"party_size": "2", "date": "friday", "time": "7:00 pm", "name": "Ana"})
    assert s.update(ref, {"time": "8:00 pm"})["time"] == "8:00 pm"
    assert s.update("VB-9999", {"time": "8:00 pm"}) is None
    assert s.cancel(ref) is True and s.get(ref)["status"] == "cancelled"
    assert s.cancel("VB-9999") is False
