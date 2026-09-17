"""SQLite-backed booking store — same interface as the in-memory one, so the
dialogue manager doesn't change. Bookings persist across restarts, which is what
makes ``lookup`` work in a real deployment. Uses the standard-library ``sqlite3``
(no dependencies); slots are stored as a JSON blob.
"""
from __future__ import annotations

import json
import sqlite3


class SqliteBookingStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._db = sqlite3.connect(path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS bookings ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, ref TEXT UNIQUE, data TEXT)"
        )
        self._db.commit()

    def create(self, slots: dict[str, str]) -> str:
        cur = self._db.execute("INSERT INTO bookings (ref, data) VALUES (NULL, ?)",
                               (json.dumps(dict(slots)),))
        ref = f"VB-{cur.lastrowid:04d}"
        self._db.execute("UPDATE bookings SET ref = ? WHERE id = ?", (ref, cur.lastrowid))
        self._db.commit()
        return ref

    def get(self, ref: str) -> dict | None:
        row = self._db.execute("SELECT data FROM bookings WHERE ref = ?", (ref,)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self) -> dict[str, dict]:
        rows = self._db.execute("SELECT ref, data FROM bookings").fetchall()
        return {ref: json.loads(data) for ref, data in rows}
