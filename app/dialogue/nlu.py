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
_DAYS = ["today", "tonight", "tomorrow", "monday", "tuesday", "wednesday",
         "thursday", "friday", "saturday", "sunday"]


def detect_intent(text: str) -> str:
    low = text.lower()
    for intent, patterns in INTENTS.items():
        if any(re.search(p, low) for p in patterns):
            return intent
    return "unknown"


def extract_slots(text: str) -> dict[str, str]:
    slots: dict[str, str] = {}

    if (m := _TIME.search(text)):
        minute = m.group(2) or "00"
        slots["time"] = f"{int(m.group(1))}:{minute} {m.group(3).lower()}"

    party = _PARTY.search(text) or _PARTY_FOR.search(text)
    if party:
        slots["party_size"] = party.group(1)

    if (m := _NAME.search(text)):
        slots["name"] = m.group(1)

    if (m := _REF.search(text)):
        slots["ref"] = f"VB-{int(m.group(1)):04d}"

    if (m := _SPECIAL.search(text)):
        slots["special_request"] = m.group(1).lower()

    low = text.lower()
    for day in _DAYS:
        if day in low:
            slots["date"] = day
            break

    return slots
