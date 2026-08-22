"""Deterministic natural-language date/time parsing (standard library only).

Rover messages phrase times casually ("Saturday at 3pm", "tomorrow at 10:30",
"this Friday", "8/23 at 4"). This module turns that free text into concrete,
timezone-aware datetimes, while being explicit about what it could NOT pin
down — so the rest of the assistant can honor the rule "never guess a date or
time when the conversation is genuinely ambiguous."

For a production system you would likely swap or augment this with an
LLM-based extractor; the :class:`~rover_assistant.extraction.Extractor`
interface exists for exactly that. This rule-based parser keeps the core
runnable and fully testable with no external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2, "weds": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

# Words that signal genuine uncertainty about the date/time itself. Proposal
# openers like "how about" or "does that work" are deliberately NOT here — they
# offer a specific time and should not be treated as tentative.
TENTATIVE_MARKERS = (
    "maybe", "possibly", "might ", "perhaps", "sometime", "tentative",
    "tentatively", "or so", "thinking about", "thinking maybe", "not sure",
    "not totally sure", "-ish", "hopefully", "if i can", "if my schedule",
)

DAYPART_AMPM = {
    "morning": "am",
    "afternoon": "pm",
    "evening": "pm",
    "night": "pm",
    "tonight": "pm",
    "noon": "pm",
}


@dataclass
class DateTimeMatch:
    dt: datetime
    has_date: bool
    has_time: bool
    # How precisely the date was stated: "explicit" (month/day, numeric, today,
    # tomorrow), "weekday" (a bare "Saturday"), or "none" (only a time).
    date_kind: str = "none"
    assumed_meridiem: bool = False  # we inferred am/pm rather than reading it
    tentative: bool = False         # local phrasing suggested it was floated
    raw: str = ""


# --------------------------------------------------------------------------- #
# Time parsing
# --------------------------------------------------------------------------- #

# 12-hour clock with explicit am/pm, optional minutes: "3pm", "3:30 p.m.", "at 11am"
_RE_TIME_AMPM = re.compile(
    r"\b(?:at\s+)?(?P<h>1[0-2]|0?[1-9])(?::(?P<m>[0-5][0-9]))?\s*(?P<ap>[ap])\.?\s*m\.?\b",
    re.IGNORECASE,
)
# 24-hour / clock with explicit minutes and no am/pm: "15:00", "9:45"
_RE_TIME_HHMM = re.compile(r"\b(?P<h>[01]?[0-9]|2[0-3]):(?P<m>[0-5][0-9])\b")
# Named times
_RE_NOON = re.compile(r"\bnoon\b", re.IGNORECASE)
_RE_MIDNIGHT = re.compile(r"\bmidnight\b", re.IGNORECASE)
# Bare "at N" with a daypart nearby, e.g. "at 3 in the afternoon", "3 tonight"
_RE_TIME_BARE = re.compile(r"\b(?:at\s+)?(?P<h>1[0-2]|0?[1-9])\b")


def _nearest_daypart(text: str) -> Optional[str]:
    low = text.lower()
    for word, ap in DAYPART_AMPM.items():
        if word in low:
            return ap
    return None


def _find_time(text: str) -> Optional[tuple[time, bool, str]]:
    """Return (time, assumed_meridiem, raw) or None."""
    m = _RE_NOON.search(text)
    if m:
        return time(12, 0), False, m.group(0)
    m = _RE_MIDNIGHT.search(text)
    if m:
        return time(0, 0), False, m.group(0)

    m = _RE_TIME_AMPM.search(text)
    if m:
        h = int(m.group("h")) % 12
        if m.group("ap").lower() == "p":
            h += 12
        minute = int(m.group("m")) if m.group("m") else 0
        return time(h, minute), False, m.group(0)

    m = _RE_TIME_HHMM.search(text)
    if m:
        return time(int(m.group("h")), int(m.group("m"))), False, m.group(0)

    # Bare hour: only accept if a daypart word disambiguates am/pm, otherwise
    # it's genuinely ambiguous and we refuse to guess.
    m = _RE_TIME_BARE.search(text)
    if m:
        ap = _nearest_daypart(text)
        h = int(m.group("h"))
        if ap is not None:
            hh = h % 12
            if ap == "pm":
                hh += 12
            return time(hh, 0), False, m.group(0)
        # No daypart: assume PM for 1-6 (typical visit hours), AM for 7-11,
        # but flag it as assumed so the caller can surface a "verify AM/PM".
        if 1 <= h <= 6:
            return time(h + 12, 0), True, m.group(0)
        if 7 <= h <= 11:
            return time(h, 0), True, m.group(0)
    return None


# --------------------------------------------------------------------------- #
# Date parsing
# --------------------------------------------------------------------------- #

_RE_MONTH_DAY = re.compile(
    r"\b(?P<mon>" + "|".join(MONTHS.keys()) + r")\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?"
    r"(?:,?\s+(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
_RE_DAY_MONTH = re.compile(
    r"\b(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<mon>" + "|".join(MONTHS.keys()) + r")\b",
    re.IGNORECASE,
)
_RE_NUMERIC = re.compile(
    r"\b(?P<m>1[0-2]|0?[1-9])/(?P<d>3[01]|[12][0-9]|0?[1-9])(?:/(?P<y>\d{2,4}))?\b"
)
_RE_WEEKDAY = re.compile(
    r"\b(?P<mod>this|next|coming)?\s*(?P<wd>" + "|".join(WEEKDAYS.keys()) + r")\b",
    re.IGNORECASE,
)
_RE_TODAY = re.compile(r"\b(today|tonight)\b", re.IGNORECASE)
_RE_TOMORROW = re.compile(r"\btomorrow\b", re.IGNORECASE)
_RE_DAY_AFTER = re.compile(r"\bday after tomorrow\b", re.IGNORECASE)


def _roll_year(candidate: date, today: date) -> date:
    """If a month/day landed clearly in the past, roll to next year."""
    if candidate < today - timedelta(days=1):
        try:
            return candidate.replace(year=candidate.year + 1)
        except ValueError:  # Feb 29
            return candidate.replace(year=candidate.year + 1, day=28)
    return candidate


def _find_date(text: str, today: date) -> Optional[tuple[date, str, str]]:
    """Return (date, raw, kind) or None. ``today`` is the reference date.

    ``kind`` is "explicit" for a fully specified date, "weekday" for a bare
    weekday name.
    """
    m = _RE_DAY_AFTER.search(text)
    if m:
        return today + timedelta(days=2), m.group(0), "explicit"
    m = _RE_TOMORROW.search(text)
    if m:
        return today + timedelta(days=1), m.group(0), "explicit"
    m = _RE_TODAY.search(text)
    if m:
        return today, m.group(0), "explicit"

    m = _RE_MONTH_DAY.search(text)
    if m:
        month = MONTHS[m.group("mon").lower()]
        day = int(m.group("day"))
        year = int(m.group("year")) if m.group("year") else today.year
        try:
            d = date(year, month, day)
        except ValueError:
            return None
        if not m.group("year"):
            d = _roll_year(d, today)
        return d, m.group(0), "explicit"

    m = _RE_DAY_MONTH.search(text)
    if m:
        month = MONTHS[m.group("mon").lower()]
        day = int(m.group("day"))
        try:
            d = date(today.year, month, day)
        except ValueError:
            return None
        return _roll_year(d, today), m.group(0), "explicit"

    m = _RE_NUMERIC.search(text)
    if m:
        month = int(m.group("m"))
        day = int(m.group("d"))
        if m.group("y"):
            y = int(m.group("y"))
            year = y + 2000 if y < 100 else y
        else:
            year = today.year
        try:
            d = date(year, month, day)
        except ValueError:
            return None
        if not m.group("y"):
            d = _roll_year(d, today)
        return d, m.group(0), "explicit"

    m = _RE_WEEKDAY.search(text)
    if m:
        target = WEEKDAYS[m.group("wd").lower()]
        base = (target - today.weekday()) % 7
        mod = (m.group("mod") or "").lower()
        if mod == "next":
            days = base + 7 if base != 0 else 7
        else:
            days = base  # 0 means today
        return today + timedelta(days=days), m.group(0), "weekday"

    return None


# --------------------------------------------------------------------------- #
# Combined
# --------------------------------------------------------------------------- #


def _is_tentative(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in TENTATIVE_MARKERS)


def parse_when(text: str, now: datetime, tz: ZoneInfo) -> Optional[DateTimeMatch]:
    """Parse the single most likely date/time from a short message.

    Returns ``None`` when nothing datelike is found. When only a date is found,
    ``has_time`` is False and the time component is midnight local. When only a
    time is found (no date), the date defaults to ``now``'s date (or the next
    day if that time already passed today).
    """
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    today = now.astimezone(tz).date()

    found_date = _find_date(text, today)
    found_time = _find_time(text)
    if not found_date and not found_time:
        return None

    if found_date:
        d, date_raw, date_kind = found_date
    else:
        d, date_raw, date_kind = today, "", "none"

    if found_time:
        t, assumed, time_raw = found_time
        has_time = True
    else:
        t, assumed, time_raw = time(0, 0), False, ""
        has_time = False

    dt = datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=tz)

    # If only a time was given and it's already past for today, assume next day.
    if has_time and not found_date and dt < now.astimezone(tz):
        dt = dt + timedelta(days=1)

    raw = " ".join(part for part in (date_raw, time_raw) if part).strip()
    return DateTimeMatch(
        dt=dt,
        has_date=bool(found_date),
        has_time=has_time,
        date_kind=date_kind,
        assumed_meridiem=assumed,
        tentative=_is_tentative(text),
        raw=raw or text.strip()[:60],
    )
