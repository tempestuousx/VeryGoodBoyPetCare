"""Compose calendar-event notes from a conversation and a commitment.

Only real information is included — structured pet/client fields plus sentences
actually present in the conversation. Nothing is invented (rule 4 & the "do not
invent information" instruction).
"""

from __future__ import annotations

import re

from .models import Commitment, Conversation, Pet

# Keywords whose sentences are worth surfacing for a booking (entry, access,
# care logistics). Used to quote real sentences, never to fabricate details.
CARE_KEYWORDS = (
    "key", "code", "lockbox", "gate", "alarm", "garage", "park", "parking",
    "leash", "harness", "feed", "food", "treat", "medication", "med ", "meds",
    "pill", "walk", "potty", "crate", "kennel", "water", "litter", "vet",
    "allerg", "afraid", "anxious", "bark", "door", "backyard", "fence",
)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _care_sentences(conv: Conversation) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for msg in conv.messages:
        for sent in _sentences(msg.text):
            low = sent.lower()
            if any(kw in low for kw in CARE_KEYWORDS):
                key = low[:80]
                if key not in seen:
                    seen.add(key)
                    out.append(sent)
    return out


def _pet_block(pet: Pet) -> list[str]:
    lines = [f"  • {pet.name}" + (f" ({pet.species})" if pet.species else "")]
    for label, value in (
        ("Feeding", pet.feeding),
        ("Medication", pet.medication),
        ("Walking", pet.walking),
        ("Behavior/routine", pet.behavior),
        ("Notes", pet.notes),
    ):
        if value:
            lines.append(f"      - {label}: {value}")
    return lines


def build_notes(
    conv: Conversation, commitment: Commitment, include_care_scan: bool = True
) -> str:
    lines: list[str] = []
    lines.append(f"Client: {conv.client.name}")
    if conv.client.phone:
        lines.append(f"Phone: {conv.client.phone}")
    if conv.pets:
        lines.append(f"Pet(s): {conv.pet_names()}")
    if commitment.service or conv.service:
        lines.append(f"Service: {commitment.service or conv.service}")
    address = conv.meeting_address()
    if address:
        lines.append(f"Address: {address}")

    if conv.pets:
        lines.append("")
        lines.append("Pet details:")
        for pet in conv.pets:
            lines.extend(_pet_block(pet))

    if include_care_scan:
        care = _care_sentences(conv)
        if care:
            lines.append("")
            lines.append("Notes from conversation:")
            for sent in care:
                lines.append(f"  • {sent}")

    if commitment.summary:
        lines.append("")
        lines.append(f"Summary: {commitment.summary}")

    if conv.url:
        lines.append("")
        lines.append(f"Rover conversation: {conv.url}")

    return "\n".join(lines)
