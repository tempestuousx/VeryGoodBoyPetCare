# Rover Booking Assistant

Turn Rover conversations into calendar events, reminders, and prepared
follow-up messages — so you never have to manually copy things between Rover
and your calendar.

```
Rover conversation  →  identify commitment  →  calendar event
                    →  appropriate reminders →  routine follow-up
```

The core is **dependency-free** (Python standard library only), so it runs and
is fully tested without any external credentials. Real integrations (Google
Calendar, an LLM extractor) plug in behind clean interfaces.

## What it does

Given a conversation, the assistant detects:

- **Proposed** vs **confirmed** meet-and-greets (a casual "maybe Saturday" is
  never booked — it's flagged).
- **Confirmed bookings** (with service, pets, times, and access details).
- **Date/time changes** (updates the existing event — never duplicates).
- **Cancellations** (cancels the event and its reminders).
- **Client requests to confirm.**
- **Your own follow-up promises** ("I'll text you tomorrow", "I'll confirm an
  hour before") → turned into reminders automatically.

For each confirmed **meet-and-greet** it creates:

| Item | Title / text | Timing |
|------|--------------|--------|
| Calendar event | `Rover Meet & Greet — [Client] / [Pet]` | at the appointment |
| Confirmation reminder | `Text Rover client to confirm meet-and-greet.` (+ client, pet, time, link) | 1 hour before* |
| "On my way" reminder | `Message [Client]: On my way.` | travel time + buffer before (fallback 20–30 min) |

\* suppressed if you already confirmed within the last few hours.

For each confirmed **booking** it creates a calendar event titled
`Rover — [Service] — [Pet]` with all care details (feeding, medication,
walking, entry/gate/alarm/parking) preserved in the notes — nothing invented.

It also drafts routine **confirmation** and **"on my way"** messages. These
require your review by default; pass `--auto-routine` to mark them
auto-sendable. Anything touching pricing, refunds, cancellations, complaints,
or safety is always held for review.

## Quick start

```bash
# Process the sample conversations, persist to a store, export an .ics
python -m rover_assistant.cli process examples/sample_conversations.json \
    --store rover_store.json --ics rover.ics --now 2026-08-22T08:00:00

# See what's tracked
python -m rover_assistant.cli list --store rover_store.json

# Re-export an .ics from the store at any time
python -m rover_assistant.cli export-ics --store rover_store.json --out rover.ics
```

Import `rover.ics` into Google/Apple/Outlook calendars, or wire up the Google
Calendar backend for live sync (see `docs/google_calendar_setup.md`).

### Running it again is safe

Every event and reminder has a stable `source_key` derived from the
conversation, so re-processing the same conversation **updates in place** — it
never creates duplicates. Change a time in Rover and re-run; the event and its
reminders move to the new time.

## Input format

Rover has no public API, so an ingestion adapter (browser export, forwarded
email, or manual entry) produces normalized JSON. See
`examples/sample_conversations.json` and the docstring in
`rover_assistant/ingest.py` for the schema.

## Architecture

```
rover_assistant/
  models.py         # dataclasses: Conversation, Commitment, CalendarEvent, Reminder, ...
  config.py         # timezone, lead times, travel time, redundant-confirm window
  datetime_parse.py # deterministic natural-language date/time parser
  extraction.py     # Extractor interface + RuleBasedExtractor (intent + commitments)
  scheduling.py     # reminder timing (confirm / on-my-way / travel time)
  notes.py          # compose calendar notes from real conversation content
  messaging.py      # message templates + "needs review" guardrail
  keys.py           # stable source_key construction (dedup)
  engine.py         # orchestrator: conversation -> events + reminders + drafts
  ingest.py         # JSON -> Conversation
  cli.py            # command line interface
  backends/
    base.py           # CalendarBackend / ReminderBackend interfaces
    local.py          # persistent JSON store (default, offline)
    ics.py            # iCalendar export
    google_calendar.py# live Google Calendar adapter (optional extra)
```

Swap the rule-based extractor for an LLM-based one by implementing the
`Extractor` protocol, or point the engine at `GoogleCalendarBackend` instead of
`LocalStore`. Nothing else changes.

## Design rules honored

1. Never create duplicate calendar events (dedup by `source_key`).
2. Never guess a date/time when genuinely ambiguous (tentative → flagged, not booked).
3. Use the most recently agreed-upon information (latest agreed time wins).
4. Preserve pet-care information in the notes (only real content, never invented).
5. Never send messages needing judgment — those are always held for review.

## Development

```bash
python -m unittest discover -t . -s tests   # 40 tests, no external deps
# or, if you have pytest:  pytest
```

## Google Calendar (optional)

```bash
pip install -e ".[google]"
```

Then follow `docs/google_calendar_setup.md` and construct the engine with
`GoogleCalendarBackend` instead of `LocalStore`.
