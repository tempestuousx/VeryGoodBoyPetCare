"""Prepared outbound messages and the guardrail on which may be automatic.

Confirmation and "on my way" notes are routine logistics and may be treated as
auto-sendable *only if* the caller explicitly opts in (``auto_routine=True``).
Anything touching pricing, booking terms, refunds, complaints, safety, or
unusual requests always requires the sitter's review — it is never auto-sent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import MessageKind, PreparedMessage

# Topics that must always be shown to the sitter before sending.
SENSITIVE = (
    "price", "pricing", "rate", "cost", "fee", "refund", "deposit", "charge",
    "cancel", "cancellation", "complaint", "unhappy", "safety", "bite", "bit ",
    "aggress", "emergency", "vet", "injur", "sick", "medication change",
    "discount", "extra charge", "policy", "terms",
)


def _fmt_time(dt: datetime) -> str:
    return dt.strftime("%-I:%M %p").lstrip("0")


def build_confirmation_message(
    conversation_id: str, appointment: datetime, auto_routine: bool
) -> PreparedMessage:
    text = (
        f"Hi! Just confirming we're still good for our meet-and-greet at "
        f"{_fmt_time(appointment)}. See you soon!"
    )
    return PreparedMessage(
        kind=MessageKind.CONFIRMATION,
        text=text,
        conversation_id=conversation_id,
        requires_approval=not auto_routine,
        reason="Routine confirmation." if auto_routine else "Review before sending.",
    )


def build_on_my_way_message(
    conversation_id: str, client_name: Optional[str], auto_routine: bool
) -> PreparedMessage:
    text = "On my way! I'll see you shortly."
    return PreparedMessage(
        kind=MessageKind.ON_MY_WAY,
        text=text,
        conversation_id=conversation_id,
        requires_approval=not auto_routine,
        reason="Routine 'on my way'." if auto_routine else "Review before sending.",
    )


def is_sensitive(text: str) -> bool:
    low = text.lower()
    return any(word in low for word in SENSITIVE)
