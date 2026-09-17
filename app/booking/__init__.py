"""Booking store — the domain action behind the voice agent.

Default is an in-memory store. Set ``VOXBRIDGE_DB=path.db`` to persist bookings
across restarts with the SQLite-backed store (same interface).
"""
import os

from .store import BookingStore

__all__ = ["BookingStore", "get_booking_store"]


def get_booking_store():
    path = os.getenv("VOXBRIDGE_DB")
    if path:
        from .sqlite_store import SqliteBookingStore

        return SqliteBookingStore(path)
    return BookingStore()
