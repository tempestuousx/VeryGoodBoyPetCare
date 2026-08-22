"""Reminder scheduling logic for meet-and-greets.

Given a confirmed meet-and-greet, compute:

* the confirmation reminder ("Text Rover client to confirm meet-and-greet"),
  one hour before by default — unless the sitter already confirmed recently,
  in which case it is redundant and suppressed;
* the "on my way" reminder, timed off travel time (or a 20-30 min fallback)
  with a small buffer so there's time to actually send the message.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .config import Config
from .models import Conversation, Sender


def already_confirmed_recently(
    conv: Conversation, appointment: datetime, window: timedelta
) -> bool:
    """True if the sitter sent a confirmation-type message within ``window``
    before the appointment (making a confirm reminder redundant)."""
    markers = (
        "confirm", "still on", "see you", "just checking we're", "we're still",
        "still good", "on for",
    )
    lower_start = appointment - window
    for msg in conv.messages:
        if msg.sender != Sender.ME:
            continue
        if lower_start <= msg.timestamp <= appointment:
            low = msg.text.lower()
            if any(m in low for m in markers):
                return True
    return False


def confirm_reminder_time(appointment: datetime, cfg: Config) -> datetime:
    return appointment - cfg.confirm_lead


def on_my_way_reminder_time(
    appointment: datetime, cfg: Config, conversation_id: str
) -> datetime:
    """When to remind the sitter to send 'On my way' and leave.

    Uses per-conversation or global travel time when known, else the default
    20-30 min fallback. Adds a send buffer so the text goes out before driving.
    """
    minutes = cfg.travel_minutes_for(conversation_id)
    if minutes is not None:
        lead = timedelta(minutes=minutes) + cfg.on_my_way_send_buffer
    else:
        lead = cfg.default_travel_lead + cfg.on_my_way_send_buffer
    return appointment - lead
