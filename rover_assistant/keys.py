"""Stable ``source_key`` construction for dedup.

A source_key uniquely and deterministically identifies the *slot* an item
occupies (this conversation's meet-and-greet event, its confirm reminder, a
particular follow-up promise). Re-processing the same conversation reproduces
the same keys, so backends update in place instead of duplicating.
"""

from __future__ import annotations

import hashlib

MG_EVENT = "mg_event"
MG_CONFIRM_REMINDER = "mg_confirm_reminder"
MG_ONMYWAY_REMINDER = "mg_onmyway_reminder"
BOOKING_EVENT = "booking_event"


def event_key(conversation_id: str, kind: str) -> str:
    return f"{conversation_id}:{kind}"


def reminder_key(conversation_id: str, kind: str) -> str:
    return f"{conversation_id}:{kind}"


def followup_key(conversation_id: str, evidence: str) -> str:
    digest = hashlib.sha1(evidence.strip().lower().encode("utf-8")).hexdigest()[:10]
    return f"{conversation_id}:followup:{digest}"
