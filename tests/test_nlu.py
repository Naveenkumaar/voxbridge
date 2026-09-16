from app.dialogue.nlu import detect_intent, extract_slots


def test_intents():
    assert detect_intent("I'd like to book a table") == "book_table"
    assert detect_intent("cancel that please") == "cancel"
    assert detect_intent("yes that's right") == "affirm"
    assert detect_intent("no") == "deny"
    assert detect_intent("hello there") == "greet"


def test_slot_extraction_time_and_party():
    slots = extract_slots("a table for 4 at 7pm")
    assert slots["party_size"] == "4"
    assert slots["time"] == "7:00 pm"


def test_slot_extraction_name_and_day():
    slots = extract_slots("book tomorrow, the name is Priya")
    assert slots["date"] == "tomorrow"
    assert slots["name"] == "Priya"


def test_party_people_phrasing():
    assert extract_slots("6 people please")["party_size"] == "6"
