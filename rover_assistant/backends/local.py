"""A local, persistent calendar + reminder store.

Backed by an in-memory dict, optionally persisted to a JSON file so dedup works
across separate runs of the CLI. This is a real, usable backend for anyone who
just wants events/reminders tracked locally (and exported to .ics), and it is
what the test suite runs against.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models import (
    CalendarEvent,
    EventStatus,
    Reminder,
    ReminderStatus,
    to_dict,
)


def _event_from_dict(d: dict) -> CalendarEvent:
    return CalendarEvent(
        title=d["title"],
        start=datetime.fromisoformat(d["start"]),
        source_key=d["source_key"],
        end=datetime.fromisoformat(d["end"]) if d.get("end") else None,
        location=d.get("location"),
        notes=d.get("notes", ""),
        conversation_id=d.get("conversation_id"),
        conversation_url=d.get("conversation_url"),
        status=EventStatus(d.get("status", "active")),
        id=d.get("id"),
    )


def _reminder_from_dict(d: dict) -> Reminder:
    return Reminder(
        text=d["text"],
        remind_at=datetime.fromisoformat(d["remind_at"]),
        source_key=d["source_key"],
        conversation_id=d.get("conversation_id"),
        conversation_url=d.get("conversation_url"),
        status=ReminderStatus(d.get("status", "active")),
        id=d.get("id"),
    )


class LocalStore:
    """Implements both CalendarBackend and ReminderBackend."""

    def __init__(self, path: Optional[str | Path] = None) -> None:
        self.path = Path(path) if path else None
        self._events: dict[str, CalendarEvent] = {}
        self._reminders: dict[str, Reminder] = {}
        self._seq = 0
        if self.path and self.path.exists():
            self._load()

    # -- persistence ------------------------------------------------------ #

    def _load(self) -> None:
        data = json.loads(self.path.read_text())
        self._seq = data.get("seq", 0)
        for d in data.get("events", []):
            ev = _event_from_dict(d)
            self._events[ev.source_key] = ev
        for d in data.get("reminders", []):
            rm = _reminder_from_dict(d)
            self._reminders[rm.source_key] = rm

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "seq": self._seq,
            "events": [to_dict(e) for e in self._events.values()],
            "reminders": [to_dict(r) for r in self._reminders.values()],
        }
        self.path.write_text(json.dumps(data, indent=2))

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-{self._seq}"

    # -- CalendarBackend -------------------------------------------------- #

    def find_event(self, source_key: str) -> Optional[CalendarEvent]:
        return self._events.get(source_key)

    def upsert_event(self, event: CalendarEvent) -> CalendarEvent:
        existing = self._events.get(event.source_key)
        if existing:
            event.id = existing.id
        else:
            event.id = self._next_id("evt")
        self._events[event.source_key] = event
        return event

    def cancel_event(self, source_key: str) -> bool:
        ev = self._events.get(source_key)
        if not ev:
            return False
        ev.status = EventStatus.CANCELLED
        return True

    def list_events(self) -> list[CalendarEvent]:
        return sorted(self._events.values(), key=lambda e: e.start)

    # -- ReminderBackend -------------------------------------------------- #

    def find_reminder(self, source_key: str) -> Optional[Reminder]:
        return self._reminders.get(source_key)

    def upsert_reminder(self, reminder: Reminder) -> Reminder:
        existing = self._reminders.get(reminder.source_key)
        if existing:
            reminder.id = existing.id
        else:
            reminder.id = self._next_id("rem")
        self._reminders[reminder.source_key] = reminder
        return reminder

    def cancel_reminder(self, source_key: str) -> bool:
        rm = self._reminders.get(source_key)
        if not rm:
            return False
        rm.status = ReminderStatus.CANCELLED
        return True

    def list_reminders(self) -> list[Reminder]:
        return sorted(self._reminders.values(), key=lambda r: r.remind_at)
