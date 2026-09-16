"""Dialogue stage — NLU + a slot-filling dialogue manager."""
from .manager import DialogueManager
from .nlu import detect_intent, extract_slots

__all__ = ["DialogueManager", "detect_intent", "extract_slots"]
