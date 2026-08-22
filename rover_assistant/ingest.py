"""Load normalized Rover conversations from JSON.

This is the ingestion adapter boundary. Rover has no public API, so something
upstream (a browser export, a forwarded-email parser, or manual entry) must
produce JSON in this shape:

    {
      "id": "conv-123",
      "url": "https://www.rover.com/messages/conv-123/",
      "service": "Drop-In Visit",
      "location": "500 Oak St, Springfield",
      "client": {"name": "Jane", "phone": "555-0100", "address": "500 Oak St"},
      "pets": [
        {"name": "Bailey", "species": "dog", "feeding": "...", "medication": "...",
         "walking": "...", "behavior": "...", "notes": "..."}
      ],
      "messages": [
        {"sender": "client", "text": "...", "timestamp": "2026-08-20T09:00:00"},
        {"sender": "me", "text": "...", "timestamp": "2026-08-20T09:05:00"}
      ]
    }

Naive timestamps are interpreted in the configured timezone.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Union
from zoneinfo import ZoneInfo

from .models import Client, Conversation, Message, Pet, Sender


def _parse_ts(value: str, tz: ZoneInfo) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return dt


def conversation_from_dict(data: dict, tz: ZoneInfo) -> Conversation:
    client_data = data.get("client", {})
    client = Client(
        name=client_data.get("name", "Unknown"),
        phone=client_data.get("phone"),
        address=client_data.get("address"),
    )
    pets = [
        Pet(
            name=p.get("name", ""),
            species=p.get("species"),
            breed=p.get("breed"),
            feeding=p.get("feeding"),
            medication=p.get("medication"),
            walking=p.get("walking"),
            behavior=p.get("behavior"),
            notes=p.get("notes"),
        )
        for p in data.get("pets", [])
    ]
    messages = [
        Message(
            sender=Sender(m["sender"]),
            text=m["text"],
            timestamp=_parse_ts(m["timestamp"], tz),
        )
        for m in data.get("messages", [])
    ]
    return Conversation(
        id=data["id"],
        client=client,
        messages=messages,
        pets=pets,
        service=data.get("service"),
        location=data.get("location"),
        url=data.get("url"),
    )


def load_conversations(path: Union[str, Path], tz: ZoneInfo) -> list[Conversation]:
    raw = json.loads(Path(path).read_text())
    items = raw if isinstance(raw, list) else [raw]
    return [conversation_from_dict(item, tz) for item in items]
