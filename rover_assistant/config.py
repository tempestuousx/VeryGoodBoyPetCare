"""Configuration for the assistant.

Keeps all tunable policy in one place: timezone, reminder lead times, travel
time defaults, and the redundant-confirmation window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional
from zoneinfo import ZoneInfo


@dataclass
class Config:
    # Timezone used to interpret bare times ("3pm") and to render reminders.
    timezone: str = "America/Los_Angeles"

    # Confirmation reminder: fire this long before the meet-and-greet.
    confirm_lead: timedelta = timedelta(hours=1)

    # If the sitter already confirmed within this window before the
    # appointment, skip the (now redundant) confirmation reminder.
    redundant_confirm_window: timedelta = timedelta(hours=3)

    # Fallback "leave now / on my way" lead time when travel time is unknown.
    # The task asks for ~20-30 minutes; we use the midpoint.
    default_travel_lead: timedelta = timedelta(minutes=25)

    # Extra buffer so there's time to actually send the "on my way" text
    # before getting in the car.
    on_my_way_send_buffer: timedelta = timedelta(minutes=5)

    # Default booking length when only a start time is given (drop-in visits).
    default_booking_duration: timedelta = timedelta(minutes=30)

    # Default meet-and-greet length.
    default_meet_greet_duration: timedelta = timedelta(minutes=30)

    # Per-conversation travel time overrides, keyed by conversation id
    # (minutes). Populated by the caller when known.
    travel_minutes_by_conversation: dict[str, int] = field(default_factory=dict)

    # A single global travel time (minutes) when the sitter's routes are
    # roughly constant. ``None`` => fall back to default_travel_lead.
    default_travel_minutes: Optional[int] = None

    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def travel_minutes_for(self, conversation_id: str) -> Optional[int]:
        if conversation_id in self.travel_minutes_by_conversation:
            return self.travel_minutes_by_conversation[conversation_id]
        return self.default_travel_minutes
