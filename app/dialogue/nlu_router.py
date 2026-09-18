"""Resolve the active NLU backend — rule-based by default, LLM opt-in.

The dialogue manager talks to NLU only through this module, so the backend can
be swapped without touching the policy. ``NLU_BACKEND`` selects it:

    (unset) / "rules"   → deterministic, offline rule-based NLU (default)
    "llm" / "ollama"    → local Ollama model, with the rule-based NLU as a
                          per-call fallback (see app/dialogue/llm_nlu.py)

The backend is resolved per call, so the LLM path degrades to rules on any
error and the demo keeps working with no model and no network.
"""
from __future__ import annotations

import os

from app.dialogue import nlu as _rules


def _backend():
    name = os.getenv("NLU_BACKEND", "rules").lower()
    if name in ("llm", "ollama"):
        from app.dialogue import llm_nlu

        return llm_nlu
    return _rules


def detect_intent(text: str) -> str:
    return _backend().detect_intent(text)


def extract_slots(text: str) -> dict[str, str]:
    return _backend().extract_slots(text)
