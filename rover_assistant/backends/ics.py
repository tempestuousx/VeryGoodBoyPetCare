"""Export calendar events and reminders to a standard iCalendar (.ics) file.

The resulting file imports into Google Calendar, Apple Calendar, and Outlook.
Reminders are written as VEVENTs with a VALARM so they surface as alerts.
Cancelled items are written with STATUS:CANCELLED.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from ..models import CalendarEvent, EventStatus, Reminder, ReminderStatus


def _fmt_utc(dt: datetime) -> str:
    from datetime import timezone
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Fold long lines to 75 octets per RFC 5545."""
    if len(line) <= 75:
        return line
    parts = [line[:75]]
    rest = line[75:]
    while rest:
        parts.append(" " + rest[:74])
        rest = rest[74:]
    return "\r\n".join(parts)


def export_ics(
    events: Iterable[CalendarEvent],
    reminders: Iterable[Reminder] = (),
    calendar_name: str = "Rover",
) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//VeryGoodBoyPetCare//Rover Assistant//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
    ]

    stamp = _fmt_utc(datetime.now().astimezone())

    for ev in events:
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{ev.id or ev.source_key}@verygoodboypetcare")
        lines.append(f"DTSTAMP:{stamp}")
        lines.append(f"DTSTART:{_fmt_utc(ev.start)}")
        if ev.end:
            lines.append(f"DTEND:{_fmt_utc(ev.end)}")
        lines.append(f"SUMMARY:{_escape(ev.title)}")
        if ev.location:
            lines.append(f"LOCATION:{_escape(ev.location)}")
        notes = ev.notes
        if ev.conversation_url:
            notes = f"{notes}\nRover: {ev.conversation_url}" if notes else ev.conversation_url
        if notes:
            lines.append(f"DESCRIPTION:{_escape(notes)}")
        if ev.status == EventStatus.CANCELLED:
            lines.append("STATUS:CANCELLED")
        lines.append("END:VEVENT")

    for rm in reminders:
        if rm.status == ReminderStatus.CANCELLED:
            continue
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{rm.id or rm.source_key}@verygoodboypetcare")
        lines.append(f"DTSTAMP:{stamp}")
        lines.append(f"DTSTART:{_fmt_utc(rm.remind_at)}")
        lines.append(f"SUMMARY:{_escape('⏰ ' + rm.text)}")
        if rm.conversation_url:
            lines.append(f"DESCRIPTION:{_escape('Rover: ' + rm.conversation_url)}")
        lines.append("BEGIN:VALARM")
        lines.append("ACTION:DISPLAY")
        lines.append(f"DESCRIPTION:{_escape(rm.text)}")
        lines.append("TRIGGER:PT0M")
        lines.append("END:VALARM")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
