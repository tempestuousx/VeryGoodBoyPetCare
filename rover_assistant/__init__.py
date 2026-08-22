"""Rover booking assistant.

Turns Rover conversations into calendar events, reminders, and prepared
follow-up messages so a sitter/walker never has to manually copy things
between Rover and their calendar.

Pipeline:

    Rover conversation -> extract commitments -> calendar events
                       -> reminders -> routine follow-up messages

The package is intentionally dependency-free (Python standard library only)
so the core logic runs and is fully testable without any external
credentials. Real integrations (Google Calendar, a reminder service, an
LLM-based extractor) plug in behind the interfaces in
``rover_assistant.backends`` and ``rover_assistant.extraction``.
"""

from .models import (
    Booking,
    CalendarEvent,
    Client,
    Commitment,
    CommitmentType,
    Confidence,
    Conversation,
    MeetAndGreet,
    Message,
    Pet,
    PreparedMessage,
    Reminder,
)
from .engine import AssistantEngine, ProcessResult

__all__ = [
    "AssistantEngine",
    "ProcessResult",
    "Booking",
    "CalendarEvent",
    "Client",
    "Commitment",
    "CommitmentType",
    "Confidence",
    "Conversation",
    "MeetAndGreet",
    "Message",
    "Pet",
    "PreparedMessage",
    "Reminder",
]

__version__ = "0.1.0"
