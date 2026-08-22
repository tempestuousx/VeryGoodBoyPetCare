"""The assistant engine: conversation -> calendar events + reminders + drafts.

This is the orchestrator that implements the objective:

    Rover conversation -> identify commitment -> calendar event
                       -> appropriate reminders -> routine follow-up

It is careful about the important rules:

* Never create duplicate calendar events (dedup by stable source_key).
* Never guess when the conversation is genuinely ambiguous (tentative
  meet-and-greets are flagged, not booked).
* Use the most recently agreed-upon information (the extractor returns the
  latest agreed time; upsert updates in place).
* Preserve pet-care information in the notes.
* Do not send messages that need judgment — those are flagged for review.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from . import keys
from .config import Config
from .extraction import Extractor, RuleBasedExtractor
from .messaging import build_confirmation_message, build_on_my_way_message
from .models import (
    CalendarEvent,
    Commitment,
    CommitmentType,
    Conversation,
    PreparedMessage,
    Reminder,
)
from .notes import build_notes
from .scheduling import (
    already_confirmed_recently,
    confirm_reminder_time,
    on_my_way_reminder_time,
)


@dataclass
class ProcessResult:
    conversation_id: str
    created_events: list[CalendarEvent] = field(default_factory=list)
    updated_events: list[CalendarEvent] = field(default_factory=list)
    cancelled_events: list[str] = field(default_factory=list)
    created_reminders: list[Reminder] = field(default_factory=list)
    updated_reminders: list[Reminder] = field(default_factory=list)
    cancelled_reminders: list[str] = field(default_factory=list)
    prepared_messages: list[PreparedMessage] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    commitments: list[Commitment] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        return self.log + [f"⚑ {f}" for f in self.flags]


class AssistantEngine:
    def __init__(
        self,
        calendar,
        reminders,
        config: Optional[Config] = None,
        extractor: Optional[Extractor] = None,
        auto_routine_messages: bool = False,
    ) -> None:
        self.calendar = calendar
        self.reminders = reminders
        self.config = config or Config()
        self.extractor = extractor or RuleBasedExtractor(self.config.tz())
        self.auto_routine_messages = auto_routine_messages

    def process(
        self, conversation: Conversation, now: Optional[datetime] = None
    ) -> ProcessResult:
        now = now or datetime.now(self.config.tz())
        result = ProcessResult(conversation_id=conversation.id)
        commitments = self.extractor.extract(conversation, now)
        result.commitments = commitments

        for c in commitments:
            handler = {
                CommitmentType.MEET_AND_GREET_CONFIRMED: self._handle_mg_confirmed,
                CommitmentType.MEET_AND_GREET_PROPOSED: self._handle_mg_proposed,
                CommitmentType.BOOKING_CONFIRMED: self._handle_booking,
                CommitmentType.CANCELLATION: self._handle_cancellation,
                CommitmentType.FOLLOW_UP_COMMITMENT: self._handle_followup,
                CommitmentType.CLIENT_CONFIRM_REQUEST: self._handle_confirm_request,
            }.get(c.type)
            if handler:
                handler(conversation, c, result, now)

        return result

    # -- meet & greet confirmed ------------------------------------------ #

    def _handle_mg_confirmed(
        self, conv: Conversation, c: Commitment, result: ProcessResult, now: datetime
    ) -> None:
        appt = c.when
        assert appt is not None
        title = f"Rover Meet & Greet — {conv.client.name}"
        if conv.pets:
            title += f" / {conv.pet_names()}"

        event = CalendarEvent(
            title=title,
            start=appt,
            end=appt + self.config.default_meet_greet_duration,
            location=c.location,
            notes=build_notes(conv, c),
            source_key=keys.event_key(conv.id, keys.MG_EVENT),
            conversation_id=conv.id,
            conversation_url=conv.url,
        )
        self._upsert_event(event, result)

        # Confirmation reminder (unless the sitter already confirmed recently).
        confirm_key = keys.reminder_key(conv.id, keys.MG_CONFIRM_REMINDER)
        if already_confirmed_recently(conv, appt, self.config.redundant_confirm_window):
            if self.reminders.find_reminder(confirm_key):
                self.reminders.cancel_reminder(confirm_key)
                result.cancelled_reminders.append(confirm_key)
            result.log.append(
                "Skipped confirmation reminder (you already confirmed recently)."
            )
        else:
            ctext = "Text Rover client to confirm meet-and-greet."
            ctext += f" Client: {conv.client.name}"
            if conv.pets:
                ctext += f" / {conv.pet_names()}"
            ctext += f". Appt {appt:%a %b %-d %-I:%M %p}."
            if conv.url:
                ctext += f" {conv.url}"
            self._upsert_reminder(
                Reminder(
                    text=ctext,
                    remind_at=confirm_reminder_time(appt, self.config),
                    source_key=confirm_key,
                    conversation_id=conv.id,
                    conversation_url=conv.url,
                ),
                result,
            )

        # "On my way" reminder.
        omw_time = on_my_way_reminder_time(appt, self.config, conv.id)
        self._upsert_reminder(
            Reminder(
                text=f"Message {conv.client.name}: On my way.",
                remind_at=omw_time,
                source_key=keys.reminder_key(conv.id, keys.MG_ONMYWAY_REMINDER),
                conversation_id=conv.id,
                conversation_url=conv.url,
            ),
            result,
        )

        # Routine confirmation draft.
        result.prepared_messages.append(
            build_confirmation_message(conv.id, appt, self.auto_routine_messages)
        )
        result.prepared_messages.append(
            build_on_my_way_message(conv.id, conv.client.name, self.auto_routine_messages)
        )

        if "AM/PM assumed" in c.summary:
            result.flags.append(
                f"Meet-and-greet time AM/PM was assumed for {conv.client.name}; "
                "verify with the client."
            )

    # -- meet & greet proposed (tentative) ------------------------------- #

    def _handle_mg_proposed(
        self, conv: Conversation, c: Commitment, result: ProcessResult, now: datetime
    ) -> None:
        if c.when and c.has_explicit_time:
            when = f" (mentioned: {c.when:%a %b %-d %-I:%M %p})"
        elif c.when:
            when = f" (mentioned: {c.when:%a %b %-d})"
        else:
            when = ""
        result.flags.append(
            f"Possible meet-and-greet with {conv.client.name} not yet confirmed"
            f"{when}. No event created — confirm a date/time first."
        )

    # -- booking --------------------------------------------------------- #

    def _handle_booking(
        self, conv: Conversation, c: Commitment, result: ProcessResult, now: datetime
    ) -> None:
        service = c.service or conv.service or "Booking"
        pets = conv.pet_names() or "Pet"
        title = f"Rover — {service} — {pets}"
        end = c.end or (c.when + self.config.default_booking_duration if c.when else None)
        event = CalendarEvent(
            title=title,
            start=c.when,
            end=end,
            location=c.location,
            notes=build_notes(conv, c),
            source_key=keys.event_key(conv.id, keys.BOOKING_EVENT),
            conversation_id=conv.id,
            conversation_url=conv.url,
        )
        self._upsert_event(event, result)

    # -- cancellation ---------------------------------------------------- #

    def _handle_cancellation(
        self, conv: Conversation, c: Commitment, result: ProcessResult, now: datetime
    ) -> None:
        for kind in (keys.MG_EVENT, keys.BOOKING_EVENT):
            key = keys.event_key(conv.id, kind)
            if self.calendar.find_event(key):
                self.calendar.cancel_event(key)
                result.cancelled_events.append(key)
                result.log.append(f"Cancelled calendar event ({kind}).")
        for kind in (keys.MG_CONFIRM_REMINDER, keys.MG_ONMYWAY_REMINDER):
            key = keys.reminder_key(conv.id, kind)
            if self.reminders.find_reminder(key):
                self.reminders.cancel_reminder(key)
                result.cancelled_reminders.append(key)
        result.log.append(f"Handled cancellation for {conv.client.name}.")

    # -- follow-up promises ---------------------------------------------- #

    def _handle_followup(
        self, conv: Conversation, c: Commitment, result: ProcessResult, now: datetime
    ) -> None:
        if c.when is None:
            result.flags.append(
                f"You promised a follow-up to {conv.client.name} but no clear time "
                f'was given: "{c.evidence.strip()[:80]}". Set a reminder time.'
            )
            return
        text = c.summary
        if conv.url:
            text += f" ({conv.url})"
        self._upsert_reminder(
            Reminder(
                text=text,
                remind_at=c.when,
                source_key=keys.followup_key(conv.id, c.evidence),
                conversation_id=conv.id,
                conversation_url=conv.url,
            ),
            result,
        )

    # -- client asked me to confirm -------------------------------------- #

    def _handle_confirm_request(
        self, conv: Conversation, c: Commitment, result: ProcessResult, now: datetime
    ) -> None:
        result.flags.append(
            f"{conv.client.name} asked you to confirm. A confirmation draft is ready."
        )
        # A confirmation draft is already added when the M&G is confirmed; if the
        # M&G isn't confirmed we still surface the request via the flag above.

    # -- backend helpers -------------------------------------------------- #

    def _upsert_event(self, event: CalendarEvent, result: ProcessResult) -> None:
        existed = self.calendar.find_event(event.source_key) is not None
        saved = self.calendar.upsert_event(event)
        if existed:
            result.updated_events.append(saved)
            result.log.append(f"Updated event: {saved.title} ({saved.start:%a %b %-d %-I:%M %p}).")
        else:
            result.created_events.append(saved)
            result.log.append(f"Created event: {saved.title} ({saved.start:%a %b %-d %-I:%M %p}).")

    def _upsert_reminder(self, reminder: Reminder, result: ProcessResult) -> None:
        existed = self.reminders.find_reminder(reminder.source_key) is not None
        saved = self.reminders.upsert_reminder(reminder)
        if existed:
            result.updated_reminders.append(saved)
            result.log.append(f"Updated reminder @ {saved.remind_at:%a %b %-d %-I:%M %p}.")
        else:
            result.created_reminders.append(saved)
            result.log.append(f"Created reminder @ {saved.remind_at:%a %b %-d %-I:%M %p}.")
