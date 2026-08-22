"""Shared test helpers."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from rover_assistant.models import Client, Conversation, Message, Pet, Sender

TZ = ZoneInfo("America/Los_Angeles")
NOW = datetime(2026, 8, 22, 8, 0, tzinfo=TZ)  # a Saturday


def msg(sender, text, offset_hours=0):
    return Message(
        sender=Sender(sender),
        text=text,
        timestamp=NOW - timedelta(days=2) + timedelta(hours=offset_hours),
    )


def conversation(cid="c1", client_name="Jane", messages=None, pets=None, **kw):
    return Conversation(
        id=cid,
        client=Client(name=client_name, phone=kw.get("phone"), address=kw.get("address")),
        messages=list(messages) if messages else [],
        pets=list(pets) if pets else [],
        service=kw.get("service"),
        location=kw.get("location"),
        url=kw.get("url"),
    )
