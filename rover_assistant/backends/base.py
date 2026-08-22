"""Backend interfaces for calendars and reminders.

Every backend is keyed on ``source_key`` — a stable identity derived from the
conversation and commitment — so the assistant can find an existing event
before creating one and thereby never produce duplicates.

The calendar and reminder methods use distinct names so a single object (like
:class:`~rover_assistant.backends.local.LocalStore`) can implement both.
"""

from __future__ import annotations

from typing import Optional, Protocol

from ..models import CalendarEvent, Reminder


class CalendarBackend(Protocol):
    def find_event(self, source_key: str) -> Optional[CalendarEvent]:
        ...

    def upsert_event(self, event: CalendarEvent) -> CalendarEvent:
        """Create the event, or update the existing one with the same source_key."""
        ...

    def cancel_event(self, source_key: str) -> bool:
        """Mark the event cancelled. Returns True if one existed."""
        ...

    def list_events(self) -> list[CalendarEvent]:
        ...


class ReminderBackend(Protocol):
    def find_reminder(self, source_key: str) -> Optional[Reminder]:
        ...

    def upsert_reminder(self, reminder: Reminder) -> Reminder:
        ...

    def cancel_reminder(self, source_key: str) -> bool:
        ...

    def list_reminders(self) -> list[Reminder]:
        ...
