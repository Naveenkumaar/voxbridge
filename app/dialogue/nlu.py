"""Rule-based NLU: intent detection + slot extraction.

Deterministic and dependency-free so it is fully testable and runs offline. A
real deployment would swap these for an LLM/classifier behind the same two
functions — ``detect_intent`` and ``extract_slots`` — without touching the
dialogue manager.

Intent order matters: ``detect_intent`` returns the first match, so more specific
intents (lookup, modify) are listed before the general ``book_table``.
"""
from __future__ import annotations

import re

INTENTS = {
    "cancel": [r"\bcancel\b", r"\bnever ?mind\b", r"\bcall it off\b"],
    "lookup": [r"look ?up", r"\bfind\b.*\b(booking|reservation|table)\b",
               r"\bcheck\b.*\b(booking|reservation)\b", r"\bstatus\b",
               r"\bwhat('?s| is)\b.*\b(booking|reservation)\b"],
    "modify": [r"\bchange\b", r"\bmodify\b", r"\bupdate\b", r"\binstead\b",
               r"\bmake it\b", r"\bmove it\b"],
    "list": [r"\b(list|show|see|all)\b.*\b(bookings?|reservations?)\b",
             r"\bmy (bookings?|reservations?)\b"],
    "faq": [r"\b(hours|open|opening|closing|timing)\b", r"\b(where|located|location|address)\b",
            r"\bparking\b", r"\b(phone|contact|number)\b", r"\bmenu\b", r"\bdress code\b"],
    "book_table": [r"\bbook\b", r"\breserv", r"\btable\b", r"\bget a table\b"],
    "greet": [r"\bhi\b", r"\bhello\b", r"\bhey\b", r"good (morning|evening|afternoon)"],
    "affirm": [r"\byes\b", r"\byep\b", r"\byeah\b", r"\bcorrect\b", r"\bthat'?s right\b"],
    "deny": [r"\bno\b", r"\bnope\b", r"\bwrong\b"],
}

_TIME = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)
_PARTY = re.compile(r"\b(\d{1,2})\s*(?:people|persons?|guests?|of us|pax)\b", re.IGNORECASE)
_PARTY_FOR = re.compile(r"\bfor\s+(\d{1,2})\b", re.IGNORECASE)
_NAME = re.compile(r"\b(?:name(?:'s| is)?|it'?s|this is)\s+([A-Z][a-z]+)\b")
_REF = re.compile(r"\bVB[-\s]?(\d{1,4})\b", re.IGNORECASE)
_SPECIAL = re.compile(
    r"\b(window seat|outdoor|patio|booth|birthday|anniversary|high ?chair|"
    r"wheelchair(?: access)?|quiet table)\b", re.IGNORECASE)
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday",
             "saturday", "sunday"]
_DAYS = ["today", "tonight", "tomorrow"] + _WEEKDAYS

# spoken clock phrasings — voice transcripts say these far more than "7:30 pm"
_NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
              "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
_HALF = re.compile(r"\bhalf past\s+(\w+)", re.IGNORECASE)
_QUARTER_PAST = re.compile(r"\bquarter past\s+(\w+)", re.IGNORECASE)
_QUARTER_TO = re.compile(r"\bquarter to\s+(\w+)", re.IGNORECASE)
_OCLOCK = re.compile(r"\b(\w+)\s+o'?clock\b", re.IGNORECASE)
# relative dates
_NEXT = re.compile(r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|"
                   r"saturday|sunday|week|weekend)\b", re.IGNORECASE)
_THIS = re.compile(r"\bthis\s+(monday|tuesday|wednesday|thursday|friday|"
                   r"saturday|sunday|weekend)\b", re.IGNORECASE)


def _hour(token: str) -> int | None:
    """Resolve '7' or 'seven' to an hour, or None if it isn't one."""
    low = token.lower()
    if low in _NUM_WORDS:
        return _NUM_WORDS[low]
    if low.isdigit() and 1 <= int(low) <= 12:
        return int(low)
    return None


def detect_intent(text: str) -> str:
    low = text.lower()
    for intent, patterns in INTENTS.items():
        if any(re.search(p, low) for p in patterns):
            return intent
    return "unknown"


def _parse_time(text: str, low: str) -> str | None:
    """A clock time from '7pm', 'noon', 'half past 7', 'quarter to 8', '7 o'clock'."""
    if (m := _TIME.search(text)):
        return f"{int(m.group(1))}:{m.group(2) or '00'} {m.group(3).lower()}"
    if "noon" in low or "midday" in low:
        return "12:00 pm"
    if "midnight" in low:
        return "12:00 am"
    if (m := _HALF.search(low)) and (h := _hour(m.group(1))) is not None:
        return f"{h}:30"
    if (m := _QUARTER_PAST.search(low)) and (h := _hour(m.group(1))) is not None:
        return f"{h}:15"
    if (m := _QUARTER_TO.search(low)) and (h := _hour(m.group(1))) is not None:
        return f"{(h - 1) or 12}:45"        # "quarter to 8" → 7:45
    if (m := _OCLOCK.search(low)) and (h := _hour(m.group(1))) is not None:
        return f"{h}:00"
    return None


def _parse_date(low: str) -> str | None:
    """A day from 'tomorrow', 'next friday', 'this weekend', 'day after tomorrow'."""
    if "day after tomorrow" in low:
        return "day after tomorrow"
    if (m := _NEXT.search(low)):
        return f"next {m.group(1).lower()}"
    if (m := _THIS.search(low)):
        return f"this {m.group(1).lower()}"
    for day in _DAYS:
        if day in low:
            return day
    return None


def extract_slots(text: str) -> dict[str, str]:
    slots: dict[str, str] = {}
    low = text.lower()

    if (t := _parse_time(text, low)):
        slots["time"] = t

    party = _PARTY.search(text) or _PARTY_FOR.search(text)
    if party:
        slots["party_size"] = party.group(1)

    if (m := _NAME.search(text)):
        slots["name"] = m.group(1)

    if (m := _REF.search(text)):
        slots["ref"] = f"VB-{int(m.group(1)):04d}"

    if (m := _SPECIAL.search(text)):
        slots["special_request"] = m.group(1).lower()

    if (d := _parse_date(low)):
        slots["date"] = d

    return slots
