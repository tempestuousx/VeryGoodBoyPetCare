"""Turn a normalized Rover conversation into detected commitments.

:class:`Extractor` is the interface; :class:`RuleBasedExtractor` is a
dependency-free implementation using keyword patterns plus the datetime parser.
An LLM-backed extractor can implement the same interface and drop straight into
:class:`~rover_assistant.engine.AssistantEngine`.

The extractor is deliberately conservative: a casual "maybe Saturday" is
reported as a *proposed* (tentative) meet-and-greet, never a confirmed one, so
the engine will not create an appointment from it.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Protocol
from zoneinfo import ZoneInfo

from .datetime_parse import DateTimeMatch, parse_when
from .models import (
    Commitment,
    CommitmentType,
    Confidence,
    Conversation,
    Sender,
)

# --------------------------------------------------------------------------- #
# Keyword vocabularies
# --------------------------------------------------------------------------- #

MG_PHRASES = (
    "meet and greet", "meet & greet", "meet-and-greet", "m&g", "meetup",
    "meet up", "meet you", "meet your", "meet the pup", "meet the dog",
    "come meet", "come by to meet", "stop by to meet", "meet in person",
)

ACCEPT = (
    "sounds good", "sounds great", "works for me", "that works", "works great",
    "that'll work", "perfect", "see you then", "see you there", "confirmed",
    "we're on", "were on", "all set", "let's do", "lets do", "count me in",
    "yes", "yeah", "yep", "sure", "booked", "deal", "great", "awesome",
    "see you", "see u", "looking forward",
)

CONFIRM_STRONG = (
    "confirmed", "see you then", "see you there", "all set", "we're on",
    "were on", "locked in", "it's a date", "its a date", "booked it",
    "see you at", "see you on", "see you sat", "see you sun", "see you mon",
    "see you tue", "see you wed", "see you thu", "see you fri",
)

CANCEL = (
    "cancel", "canceled", "cancelled", "call it off", "can't make it",
    "cannot make it", "can not make it", "won't be able to make",
    "have to cancel", "need to cancel", "gotta cancel", "back out",
)

CHANGE = (
    "reschedule", "move it", "move to", "push to", "push it", "change to",
    "switch to", "instead of", "different time", "another time",
    "can we do", "actually can we", "actually let's", "actually lets",
    "bump it", "bump to", "make it",
)

BOOKING = (
    "booking confirmed", "booking is confirmed", "reservation confirmed",
    "request accepted", "you're booked", "you are booked", "booking request",
    "confirmed booking", "booked you", "just booked", "officially booked",
    "request has been accepted", "your booking",
)

FOLLOWUP = (
    "i'll text", "ill text", "i'll confirm", "ill confirm", "i'll let you know",
    "ill let you know", "i'll get back", "ill get back", "i'll send", "ill send",
    "i'll reach out", "ill reach out", "i'll check my schedule",
    "ill check my schedule", "i will text", "i will confirm",
    "i will let you know", "i will send", "i'll message", "ill message",
    "i'll update you", "ill update you", "i'll follow up", "ill follow up",
    "i'll be in touch", "ill be in touch", "i'll call", "ill call",
)

CONFIRM_REQUEST = (
    "can you confirm", "please confirm", "are we still on", "still good for",
    "still on for", "just confirming", "confirm our", "confirm the",
    "let me know if that works", "let me know if that still works",
    "does that still work", "can you let me know",
)


def _contains(text: str, phrases) -> bool:
    low = text.lower()
    return any(p in low for p in phrases)


# --------------------------------------------------------------------------- #
# Extractor interface
# --------------------------------------------------------------------------- #


class Extractor(Protocol):
    def extract(
        self, conversation: Conversation, now: datetime
    ) -> list[Commitment]:  # pragma: no cover - interface
        ...


class RuleBasedExtractor:
    def __init__(self, tz: ZoneInfo) -> None:
        self.tz = tz

    # -- public ----------------------------------------------------------- #

    def extract(self, conversation: Conversation, now: datetime) -> list[Commitment]:
        commitments: list[Commitment] = []

        mg = self._detect_meet_greet(conversation, now)
        if mg:
            commitments.append(mg)

        booking = self._detect_booking(conversation, now)
        if booking:
            commitments.append(booking)

        appt_dt = mg.when if (mg and mg.type == CommitmentType.MEET_AND_GREET_CONFIRMED) else None
        commitments.extend(self._detect_followups(conversation, now, appt_dt))

        req = self._detect_confirm_request(conversation)
        if req:
            commitments.append(req)

        return commitments

    # -- meet & greet ----------------------------------------------------- #

    def _detect_meet_greet(
        self, conv: Conversation, now: datetime
    ) -> Optional[Commitment]:
        if not any(_contains(m.text, MG_PHRASES) for m in conv.messages):
            return None

        last_concrete: Optional[DateTimeMatch] = None
        last_proposer: Optional[Sender] = None
        confirmed: Optional[DateTimeMatch] = None
        confirmed_idx = -1
        cancel_idx = -1
        tentative_seen: Optional[DateTimeMatch] = None
        evidence = ""

        for idx, msg in enumerate(conv.messages):
            low = msg.text.lower()

            if _contains(msg.text, CANCEL):
                cancel_idx = idx

            match = parse_when(msg.text, now, self.tz)
            if match and match.has_time and not match.tentative:
                accepts = _contains(msg.text, ACCEPT) or _contains(msg.text, CONFIRM_STRONG)
                # Is this an echo of the standing proposal (e.g. client says
                # "Saturday at 3pm works" to accept a proposed "August 29 3pm")
                # rather than a brand-new, more specific date? If so, keep the
                # precise standing proposal instead of downgrading it.
                is_echo = (
                    last_concrete is not None
                    and accepts
                    and match.date_kind in ("weekday", "none")
                    and match.dt.hour == last_concrete.dt.hour
                    and match.dt.minute == last_concrete.dt.minute
                    and (
                        match.date_kind == "none"
                        or match.dt.weekday() == last_concrete.dt.weekday()
                    )
                )
                if is_echo:
                    confirmed = last_concrete
                    confirmed_idx = idx
                    evidence = msg.text
                    continue  # do not replace the precise standing proposal
                # A concrete, non-tentative time proposal/agreement.
                if _contains(msg.text, CONFIRM_STRONG) or (
                    last_concrete is not None and _contains(msg.text, ACCEPT)
                ):
                    confirmed = match
                    confirmed_idx = idx
                    evidence = msg.text
                last_concrete = match
                last_proposer = msg.sender
            elif match and (match.tentative or not match.has_time):
                tentative_seen = match
            else:
                # No new time; a bare acceptance confirms the standing proposal.
                if last_concrete is not None and _contains(msg.text, ACCEPT):
                    # Only if the accepter differs from the last proposer, or the
                    # message uses strong confirm language.
                    if msg.sender != last_proposer or _contains(msg.text, CONFIRM_STRONG):
                        confirmed = last_concrete
                        confirmed_idx = idx
                        evidence = msg.text

        service = conv.service
        location = conv.meeting_address()

        # Cancellation after a confirmation wins.
        if cancel_idx > confirmed_idx and cancel_idx != -1:
            return Commitment(
                type=CommitmentType.CANCELLATION,
                conversation_id=conv.id,
                confidence=Confidence.CONFIRMED,
                when=confirmed.dt if confirmed else (last_concrete.dt if last_concrete else None),
                location=location,
                service=service,
                summary="Meet-and-greet cancelled by client.",
                evidence=conv.messages[cancel_idx].text,
            )

        if confirmed is not None:
            warn = " (⚠ AM/PM assumed — verify)" if confirmed.assumed_meridiem else ""
            return Commitment(
                type=CommitmentType.MEET_AND_GREET_CONFIRMED,
                conversation_id=conv.id,
                confidence=Confidence.CONFIRMED,
                when=confirmed.dt,
                has_explicit_time=True,
                location=location,
                service=service,
                summary=f"Meet-and-greet confirmed for {confirmed.dt:%A %b %-d at %-I:%M %p}{warn}.",
                evidence=evidence,
            )

        # Nothing confirmed: report a (tentative) proposal so it can be flagged.
        proposal = last_concrete or tentative_seen
        if proposal is not None:
            return Commitment(
                type=CommitmentType.MEET_AND_GREET_PROPOSED,
                conversation_id=conv.id,
                confidence=Confidence.TENTATIVE,
                when=proposal.dt,
                has_explicit_time=proposal.has_time,
                location=location,
                service=service,
                summary="Meet-and-greet discussed but not clearly confirmed.",
                evidence=proposal.raw,
            )
        return None

    # -- booking ---------------------------------------------------------- #

    def _detect_booking(
        self, conv: Conversation, now: datetime
    ) -> Optional[Commitment]:
        booking_msgs = [m for m in conv.messages if _contains(m.text, BOOKING)]
        if not booking_msgs:
            return None

        # Use the most recent booking-related message for the date/time.
        start_dt: Optional[datetime] = None
        end_dt: Optional[datetime] = None
        has_time = False
        evidence = ""
        for msg in booking_msgs:
            for chunk in _split_range(msg.text):
                match = parse_when(chunk, now, self.tz)
                if match:
                    if start_dt is None:
                        start_dt = match.dt
                        has_time = match.has_time
                        evidence = msg.text
                    else:
                        end_dt = match.dt

        # If no date in the booking message itself, fall back to any concrete
        # date elsewhere in the conversation.
        if start_dt is None:
            for msg in conv.messages:
                match = parse_when(msg.text, now, self.tz)
                if match and match.has_time and not match.tentative:
                    start_dt, has_time, evidence = match.dt, True, msg.text
                    break

        if start_dt is None:
            return None  # booking mentioned but no clear date -> flag, don't guess

        return Commitment(
            type=CommitmentType.BOOKING_CONFIRMED,
            conversation_id=conv.id,
            confidence=Confidence.CONFIRMED,
            when=start_dt,
            end=end_dt,
            has_explicit_time=has_time,
            location=conv.meeting_address(),
            service=conv.service,
            summary=f"Rover booking confirmed for {conv.service or 'service'}.",
            evidence=evidence,
        )

    # -- follow-up commitments (things I promised) ------------------------ #

    def _detect_followups(
        self, conv: Conversation, now: datetime, appt_dt: Optional[datetime]
    ) -> list[Commitment]:
        out: list[Commitment] = []
        for msg in conv.messages:
            if msg.sender != Sender.ME:
                continue
            if not _contains(msg.text, FOLLOWUP):
                continue

            low = msg.text.lower()
            when: Optional[datetime] = None

            if "before" in low and appt_dt is not None:
                # "I'll confirm an hour before" and similar.
                when = appt_dt - timedelta(hours=1)
            else:
                match = parse_when(msg.text, now, self.tz)
                if match:
                    when = match.dt
                    if not match.has_time:
                        when = _default_followup_time(when, low)

            out.append(
                Commitment(
                    type=CommitmentType.FOLLOW_UP_COMMITMENT,
                    conversation_id=conv.id,
                    confidence=Confidence.CONFIRMED if when else Confidence.TENTATIVE,
                    when=when,
                    has_explicit_time=when is not None,
                    summary=_summarize_followup(msg.text),
                    evidence=msg.text,
                    made_by=Sender.ME,
                )
            )
        return out

    # -- client asking me to confirm -------------------------------------- #

    def _detect_confirm_request(self, conv: Conversation) -> Optional[Commitment]:
        for msg in reversed(conv.messages):
            if msg.sender == Sender.CLIENT and _contains(msg.text, CONFIRM_REQUEST):
                return Commitment(
                    type=CommitmentType.CLIENT_CONFIRM_REQUEST,
                    conversation_id=conv.id,
                    confidence=Confidence.CONFIRMED,
                    summary="Client asked you to confirm the appointment.",
                    evidence=msg.text,
                    made_by=Sender.CLIENT,
                )
        return None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _split_range(text: str) -> list[str]:
    """Split a "start to end" phrase into two chunks (plus the whole)."""
    lowered = text.lower()
    for sep in (" until ", " through ", " to ", " - ", " – ", "–", "—"):
        if sep in lowered:
            idx = lowered.index(sep)
            return [text[:idx], text[idx + len(sep):]]
    return [text]


def _default_followup_time(dt: datetime, low: str) -> datetime:
    """Pick a sensible clock time for a date-only follow-up promise."""
    if "tonight" in low or "evening" in low:
        return dt.replace(hour=19, minute=0)
    if "afternoon" in low:
        return dt.replace(hour=14, minute=0)
    if "morning" in low:
        return dt.replace(hour=9, minute=0)
    # Generic "tomorrow" / a bare weekday: late morning is a safe default.
    return dt.replace(hour=9, minute=0)


def _summarize_followup(text: str) -> str:
    stripped = " ".join(text.split())
    if len(stripped) > 120:
        stripped = stripped[:117] + "..."
    return f'Follow up as promised: "{stripped}"'
