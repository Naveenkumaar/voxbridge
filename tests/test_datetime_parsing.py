"""Richer relative date/time parsing in the rule-based NLU."""
import pytest

from app.dialogue.nlu import extract_slots


@pytest.mark.parametrize("text,expected", [
    ("book at 7pm", "7:00 pm"),
    ("let's do noon", "12:00 pm"),
    ("around midnight", "12:00 am"),
    ("half past 7", "7:30"),
    ("quarter past 8", "8:15"),
    ("quarter to 8", "7:45"),
    ("quarter to 1", "12:45"),          # wraps to 12
    ("seven o'clock", "7:00"),
    ("at 9 oclock", "9:00"),
])
def test_time_phrasings(text, expected):
    assert extract_slots(text).get("time") == expected


@pytest.mark.parametrize("text,expected", [
    ("tomorrow", "tomorrow"),
    ("this friday", "this friday"),
    ("next friday", "next friday"),      # not just "friday"
    ("next week", "next week"),
    ("this weekend", "this weekend"),
    ("day after tomorrow", "day after tomorrow"),
])
def test_date_phrasings(text, expected):
    assert extract_slots(text).get("date") == expected


def test_combined_phrasing():
    slots = extract_slots("a table for 4 next friday at half past 7")
    assert slots["date"] == "next friday"
    assert slots["time"] == "7:30"
    assert slots["party_size"] == "4"


def test_non_hours_are_ignored():
    # "quarter to 20" isn't a clock hour → no bogus time slot
    assert "time" not in extract_slots("quarter to 20 people showed up")
