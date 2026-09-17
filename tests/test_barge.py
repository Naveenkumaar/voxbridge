"""Barge-in: speech halts as soon as the interrupt signal fires."""
from app.audio import chunk_text, speak_interruptible


def test_chunk_text_reassembles():
    chunks = chunk_text("please book a table")
    assert "".join(chunks) == "please book a table"
    assert chunks[0] == "please" and chunks[1] == " book"


def test_full_speech_when_never_interrupted():
    text = "your table for four is confirmed"
    spoken, interrupted = speak_interruptible(chunk_text(text), lambda: False)
    assert spoken == text
    assert interrupted is False


def test_interrupt_after_n_chunks_truncates():
    text = "your table for four is confirmed"
    calls = {"n": 0}

    def should_interrupt():
        calls["n"] += 1
        return calls["n"] > 3          # interrupt before the 4th chunk

    spoken, interrupted = speak_interruptible(chunk_text(text), should_interrupt)
    assert interrupted is True
    assert spoken == "your table for"   # only the first three chunks made it out
    assert len(spoken) < len(text)


def test_interrupt_at_the_very_start_speaks_nothing():
    spoken, interrupted = speak_interruptible(chunk_text("hello there"), lambda: True)
    assert spoken == "" and interrupted is True


def test_on_chunk_callback_receives_spoken_chunks():
    heard = []
    speak_interruptible(chunk_text("a b c"), lambda: False, on_chunk=heard.append)
    assert "".join(heard) == "a b c"
