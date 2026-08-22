"""Core data models for the Rover booking assistant.

All models are plain dataclasses so they serialize cleanly to/from JSON and
are easy to reason about in tests. Datetimes are always timezone-aware.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Enumerations
# --------------------------------------------------------------------------- #


class Confidence(str, enum.Enum):
    """How sure we are that a detected date/time is a real commitment.

    ``TENTATIVE`` means the conversation only floated a possibility
    ("maybe Saturday"); the assistant must NOT create appointments from it.
    ``CONFIRMED`` means the date and time are reasonably clear.
    """

    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"


class CommitmentType(str, enum.Enum):
    """Kinds of future obligation the assistant looks for in a conversation."""

    MEET_AND_GREET_PROPOSED = "meet_and_greet_proposed"
    MEET_AND_GREET_CONFIRMED = "meet_and_greet_confirmed"
    BOOKING_CONFIRMED = "booking_confirmed"
    SCHEDULE_CHANGE = "schedule_change"
    CANCELLATION = "cancellation"
    CLIENT_CONFIRM_REQUEST = "client_confirm_request"
    FOLLOW_UP_COMMITMENT = "follow_up_commitment"
    OTHER_OBLIGATION = "other_obligation"


class EventStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class ReminderStatus(str, enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    SENT = "sent"


class Sender(str, enum.Enum):
    ME = "me"          # the sitter / account owner
    CLIENT = "client"  # the Rover client


class MessageKind(str, enum.Enum):
    CONFIRMATION = "confirmation"
    ON_MY_WAY = "on_my_way"
    OTHER = "other"


# --------------------------------------------------------------------------- #
# Domain entities
# --------------------------------------------------------------------------- #


@dataclass
class Pet:
    name: str
    species: Optional[str] = None
    breed: Optional[str] = None
    feeding: Optional[str] = None
    medication: Optional[str] = None
    walking: Optional[str] = None
    behavior: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Client:
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None


@dataclass
class Message:
    sender: Sender
    text: str
    timestamp: datetime

    def __post_init__(self) -> None:
        if isinstance(self.sender, str):
            self.sender = Sender(self.sender)


@dataclass
class Conversation:
    """A normalized Rover conversation.

    This is the adapter boundary. Rover has no public API, so an ingestion
    adapter (scrape, export, forwarded email, manual entry) is responsible for
    producing this structure. Everything downstream operates on it.
    """

    id: str
    client: Client
    messages: list[Message] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)
    service: Optional[str] = None
    location: Optional[str] = None  # meeting address, if distinct from client.address
    url: Optional[str] = None       # link/reference back to the Rover conversation

    def pet_names(self) -> str:
        names = [p.name for p in self.pets if p.name]
        if not names:
            return ""
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} & {names[1]}"
        return ", ".join(names[:-1]) + f" & {names[-1]}"

    def meeting_address(self) -> Optional[str]:
        return self.location or self.client.address


@dataclass
class Commitment:
    """A future obligation detected in a conversation."""

    type: CommitmentType
    conversation_id: str
    confidence: Confidence
    when: Optional[datetime] = None       # appointment / due time
    end: Optional[datetime] = None        # for bookings with an end time
    has_explicit_time: bool = False       # False => only a date was found
    location: Optional[str] = None
    service: Optional[str] = None
    summary: str = ""
    evidence: str = ""                    # the message text this was drawn from
    made_by: Optional[Sender] = None      # who created the obligation


# Convenience aliases used by the engine/CLI for readability. They are the
# same shape as Commitment but make intent clearer at call sites.
MeetAndGreet = Commitment
Booking = Commitment


@dataclass
class CalendarEvent:
    title: str
    start: datetime
    source_key: str                       # stable identity for dedup
    end: Optional[datetime] = None
    location: Optional[str] = None
    notes: str = ""
    conversation_id: Optional[str] = None
    conversation_url: Optional[str] = None
    status: EventStatus = EventStatus.ACTIVE
    id: Optional[str] = None              # assigned by the calendar backend

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = EventStatus(self.status)


@dataclass
class Reminder:
    text: str
    remind_at: datetime
    source_key: str                       # stable identity for dedup
    conversation_id: Optional[str] = None
    conversation_url: Optional[str] = None
    status: ReminderStatus = ReminderStatus.ACTIVE
    id: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = ReminderStatus(self.status)


@dataclass
class PreparedMessage:
    """A drafted outbound message. Never auto-sent unless explicitly allowed."""

    kind: MessageKind
    text: str
    conversation_id: str
    requires_approval: bool = True
    reason: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            self.kind = MessageKind(self.kind)


# --------------------------------------------------------------------------- #
# (De)serialization helpers
# --------------------------------------------------------------------------- #


def to_dict(obj: Any) -> dict:
    """Serialize a dataclass to a JSON-safe dict (datetimes -> ISO strings)."""

    def convert(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, enum.Enum):
            return value.value
        if isinstance(value, dict):
            return {k: convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [convert(v) for v in value]
        return value

    return {k: convert(v) for k, v in asdict(obj).items()}
