"""In-memory booking store.

Deterministic confirmation refs (no randomness) so tests and demos are
reproducible. Swap for a real database behind the same ``create``/``get``
interface without touching the dialogue layer.
"""
from __future__ import annotations


class BookingStore:
    def __init__(self) -> None:
        self._bookings: dict[str, dict] = {}
        self._seq = 0

    def create(self, slots: dict[str, str]) -> str:
        self._seq += 1
        ref = f"VB-{self._seq:04d}"
        self._bookings[ref] = dict(slots)
        return ref

    def get(self, ref: str) -> dict | None:
        return self._bookings.get(ref)

    def all(self) -> dict[str, dict]:
        return dict(self._bookings)

    def update(self, ref: str, changes: dict[str, str]) -> dict | None:
        """Merge non-empty changes into an existing booking; None if not found."""
        b = self._bookings.get(ref)
        if b is None:
            return None
        b.update({k: v for k, v in changes.items() if v is not None})
        return dict(b)

    def cancel(self, ref: str) -> bool:
        """Mark a booking cancelled (kept, not deleted); False if not found."""
        b = self._bookings.get(ref)
        if b is None:
            return False
        b["status"] = "cancelled"
        return True
