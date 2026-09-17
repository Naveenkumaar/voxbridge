"""SQLite booking store persists across instances (survives 'restart')."""
import os
import tempfile

from app.booking import BookingStore, get_booking_store
from app.booking.sqlite_store import SqliteBookingStore


def test_sqlite_store_persists_across_instances():
    path = os.path.join(tempfile.mkdtemp(), "bookings.db")
    slots = {"date": "tomorrow", "time": "7:00 pm", "party_size": "4", "name": "Naveen"}

    ref = SqliteBookingStore(path).create(slots)      # write, then drop the instance
    assert ref.startswith("VB-")

    reopened = SqliteBookingStore(path)               # a fresh "process"
    assert reopened.get(ref) == slots
    assert ref in reopened.all()


def test_refs_increment_in_sqlite():
    path = os.path.join(tempfile.mkdtemp(), "b.db")
    store = SqliteBookingStore(path)
    r1 = store.create({"name": "A"})
    r2 = store.create({"name": "B"})
    assert r1 != r2 and r1 == "VB-0001" and r2 == "VB-0002"


def test_factory_defaults_to_in_memory(monkeypatch):
    monkeypatch.delenv("VOXBRIDGE_DB", raising=False)
    assert isinstance(get_booking_store(), BookingStore)


def test_factory_uses_sqlite_when_env_set(monkeypatch):
    path = os.path.join(tempfile.mkdtemp(), "env.db")
    monkeypatch.setenv("VOXBRIDGE_DB", path)
    assert isinstance(get_booking_store(), SqliteBookingStore)
