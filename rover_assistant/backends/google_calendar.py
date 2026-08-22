"""Google Calendar backend.

Real adapter that talks to the Google Calendar API. It imports the Google
client libraries lazily so the rest of the package stays dependency-free; if
they are not installed (or credentials are missing) construction raises a
clear error telling you what to install and configure.

Dedup: each event stores its ``source_key`` in
``extendedProperties.private.source_key`` and is looked up by that key, so
re-processing a conversation updates the existing event instead of duplicating.

Reminders map to Google Calendar events with a popup reminder override.

Setup (one time):

    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Provide OAuth credentials via a token file. See docs/google_calendar_setup.md.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..models import CalendarEvent, EventStatus, Reminder


class GoogleCalendarBackend:
    def __init__(
        self,
        calendar_id: str = "primary",
        credentials=None,
        service=None,
    ) -> None:
        self.calendar_id = calendar_id
        if service is not None:
            self.service = service
            return
        try:
            from googleapiclient.discovery import build  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on env
            raise RuntimeError(
                "Google Calendar backend requires the Google client libraries. "
                "Install them with:\n"
                "  pip install google-api-python-client google-auth-httplib2 "
                "google-auth-oauthlib\n"
                "then pass credentials (see docs/google_calendar_setup.md)."
            ) from exc
        if credentials is None:  # pragma: no cover - depends on env
            raise RuntimeError(
                "GoogleCalendarBackend needs OAuth credentials. See "
                "docs/google_calendar_setup.md."
            )
        self.service = build("calendar", "v3", credentials=credentials)

    # -- helpers ---------------------------------------------------------- #

    def _to_body(self, event: CalendarEvent) -> dict:
        body = {
            "summary": event.title,
            "start": {"dateTime": event.start.isoformat()},
            "end": {"dateTime": (event.end or event.start).isoformat()},
            "extendedProperties": {"private": {"source_key": event.source_key}},
        }
        description = event.notes or ""
        if event.conversation_url:
            description = (
                f"{description}\n\nRover conversation: {event.conversation_url}"
                if description
                else f"Rover conversation: {event.conversation_url}"
            )
        if description:
            body["description"] = description
        if event.location:
            body["location"] = event.location
        if event.status == EventStatus.CANCELLED:
            body["status"] = "cancelled"
        return body

    def _find_raw(self, source_key: str) -> Optional[dict]:  # pragma: no cover - network
        resp = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                privateExtendedProperty=f"source_key={source_key}",
                showDeleted=False,
                maxResults=1,
            )
            .execute()
        )
        items = resp.get("items", [])
        return items[0] if items else None

    @staticmethod
    def _from_raw(raw: dict) -> CalendarEvent:  # pragma: no cover - network
        start = raw["start"].get("dateTime") or raw["start"].get("date")
        end = raw.get("end", {}).get("dateTime")
        sk = raw.get("extendedProperties", {}).get("private", {}).get("source_key", "")
        return CalendarEvent(
            title=raw.get("summary", ""),
            start=datetime.fromisoformat(start),
            end=datetime.fromisoformat(end) if end else None,
            location=raw.get("location"),
            notes=raw.get("description", ""),
            source_key=sk,
            status=EventStatus.CANCELLED
            if raw.get("status") == "cancelled"
            else EventStatus.ACTIVE,
            id=raw.get("id"),
        )

    # -- CalendarBackend -------------------------------------------------- #

    def find_event(self, source_key: str) -> Optional[CalendarEvent]:  # pragma: no cover
        raw = self._find_raw(source_key)
        return self._from_raw(raw) if raw else None

    def upsert_event(self, event: CalendarEvent) -> CalendarEvent:  # pragma: no cover
        existing = self._find_raw(event.source_key)
        body = self._to_body(event)
        if existing:
            updated = (
                self.service.events()
                .update(calendarId=self.calendar_id, eventId=existing["id"], body=body)
                .execute()
            )
        else:
            updated = (
                self.service.events()
                .insert(calendarId=self.calendar_id, body=body)
                .execute()
            )
        event.id = updated.get("id")
        return event

    def cancel_event(self, source_key: str) -> bool:  # pragma: no cover
        existing = self._find_raw(source_key)
        if not existing:
            return False
        self.service.events().delete(
            calendarId=self.calendar_id, eventId=existing["id"]
        ).execute()
        return True

    def list_events(self) -> list[CalendarEvent]:  # pragma: no cover
        resp = self.service.events().list(calendarId=self.calendar_id).execute()
        return [self._from_raw(i) for i in resp.get("items", [])]

    # -- ReminderBackend (reminders as timed events w/ popup) ------------- #

    def upsert_reminder(self, reminder: Reminder) -> Reminder:  # pragma: no cover
        body = {
            "summary": f"⏰ {reminder.text}",
            "start": {"dateTime": reminder.remind_at.isoformat()},
            "end": {"dateTime": reminder.remind_at.isoformat()},
            "extendedProperties": {"private": {"source_key": reminder.source_key}},
            "reminders": {"useDefault": False, "overrides": [
                {"method": "popup", "minutes": 0}
            ]},
        }
        if reminder.conversation_url:
            body["description"] = f"Rover conversation: {reminder.conversation_url}"
        existing = self._find_raw(reminder.source_key)
        if existing:
            self.service.events().update(
                calendarId=self.calendar_id, eventId=existing["id"], body=body
            ).execute()
        else:
            created = (
                self.service.events()
                .insert(calendarId=self.calendar_id, body=body)
                .execute()
            )
            reminder.id = created.get("id")
        return reminder

    def find_reminder(self, source_key: str) -> Optional[Reminder]:  # pragma: no cover
        raw = self._find_raw(source_key)
        if not raw:
            return None
        start = raw["start"].get("dateTime")
        return Reminder(
            text=raw.get("summary", "").removeprefix("⏰ "),
            remind_at=datetime.fromisoformat(start),
            source_key=source_key,
            id=raw.get("id"),
        )

    def cancel_reminder(self, source_key: str) -> bool:  # pragma: no cover
        return self.cancel_event(source_key)

    def list_reminders(self) -> list[Reminder]:  # pragma: no cover
        return []
