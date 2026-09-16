"""Optional LLM-backed NLU (drop-in for the rule-based ``nlu``).

Not wired by default — the rule-based NLU keeps the demo deterministic and
offline. This shows how you would swap in a local Ollama model for intent + slot
extraction behind the exact same ``detect_intent`` / ``extract_slots`` contract.
"""
from __future__ import annotations

import json
import os

_SYSTEM = (
    "You extract a booking intent and slots from a diner's message. "
    "Reply ONLY with JSON: {\"intent\": one of "
    "[book_table,cancel,greet,affirm,deny,unknown], "
    "\"slots\": {date?,time?,party_size?,name?}}."
)


def _query(text: str) -> dict:
    import httpx

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    prompt = f"{_SYSTEM}\n\nMessage: {text}\nJSON:"
    resp = httpx.post(
        f"{host}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False, "format": "json"},
        timeout=60,
    )
    resp.raise_for_status()
    return json.loads(resp.json()["response"])


def detect_intent(text: str) -> str:
    try:
        return _query(text).get("intent", "unknown")
    except Exception:
        from app.dialogue.nlu import detect_intent as fallback

        return fallback(text)


def extract_slots(text: str) -> dict[str, str]:
    try:
        return {k: str(v) for k, v in _query(text).get("slots", {}).items() if v}
    except Exception:
        from app.dialogue.nlu import extract_slots as fallback

        return fallback(text)
