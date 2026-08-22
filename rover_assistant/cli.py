"""Command-line interface for the Rover booking assistant.

Examples
--------
Process a conversations file, persist to a store, and export an .ics::

    python -m rover_assistant.cli process examples/sample_conversations.json \\
        --store rover_store.json --ics rover.ics

Show what's currently tracked::

    python -m rover_assistant.cli list --store rover_store.json

Re-export an .ics from the store::

    python -m rover_assistant.cli export-ics --store rover_store.json --out rover.ics
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from .backends.ics import export_ics
from .backends.local import LocalStore
from .config import Config
from .engine import AssistantEngine
from .ingest import load_conversations
from .models import to_dict


def _build_config(args) -> Config:
    cfg = Config()
    if args.tz:
        cfg.timezone = args.tz
    if getattr(args, "travel_minutes", None) is not None:
        cfg.default_travel_minutes = args.travel_minutes
    return cfg


def _resolve_now(args, tz: ZoneInfo) -> datetime:
    if args.now:
        dt = datetime.fromisoformat(args.now)
        return dt if dt.tzinfo else dt.replace(tzinfo=tz)
    return datetime.now(tz)


def cmd_process(args) -> int:
    cfg = _build_config(args)
    tz = cfg.tz()
    now = _resolve_now(args, tz)
    store = LocalStore(args.store)
    engine = AssistantEngine(
        calendar=store,
        reminders=store,
        config=cfg,
        auto_routine_messages=args.auto_routine,
    )
    conversations = load_conversations(args.conversations, tz)

    all_results = []
    for conv in conversations:
        result = engine.process(conv, now=now)
        all_results.append(result)
        if not args.json:
            print(f"\n=== {conv.client.name} (conversation {conv.id}) ===")
            for line in result.summary_lines():
                print(f"  {line}")
            for msg in result.prepared_messages:
                tag = "AUTO" if not msg.requires_approval else "REVIEW"
                print(f"  ✉ [{tag}] {msg.kind.value}: {msg.text}")

    store.save()

    if args.ics:
        ics = export_ics(store.list_events(), store.list_reminders())
        with open(args.ics, "w") as fh:
            fh.write(ics)
        if not args.json:
            print(f"\nWrote {args.ics}")

    if args.json:
        import json

        payload = [
            {
                "conversation_id": r.conversation_id,
                "created_events": [to_dict(e) for e in r.created_events],
                "updated_events": [to_dict(e) for e in r.updated_events],
                "cancelled_events": r.cancelled_events,
                "created_reminders": [to_dict(x) for x in r.created_reminders],
                "updated_reminders": [to_dict(x) for x in r.updated_reminders],
                "cancelled_reminders": r.cancelled_reminders,
                "prepared_messages": [to_dict(m) for m in r.prepared_messages],
                "flags": r.flags,
                "log": r.log,
            }
            for r in all_results
        ]
        print(json.dumps(payload, indent=2))
    return 0


def cmd_list(args) -> int:
    store = LocalStore(args.store)
    print("Calendar events:")
    for ev in store.list_events():
        status = "" if ev.status.value == "active" else f" [{ev.status.value}]"
        print(f"  • {ev.start:%a %b %-d %-I:%M %p}  {ev.title}{status}")
        if ev.location:
            print(f"      @ {ev.location}")
    print("\nReminders:")
    for rm in store.list_reminders():
        status = "" if rm.status.value == "active" else f" [{rm.status.value}]"
        print(f"  • {rm.remind_at:%a %b %-d %-I:%M %p}  {rm.text}{status}")
    return 0


def cmd_export_ics(args) -> int:
    store = LocalStore(args.store)
    ics = export_ics(store.list_events(), store.list_reminders())
    with open(args.out, "w") as fh:
        fh.write(ics)
    print(f"Wrote {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="rover_assistant", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pp = sub.add_parser("process", help="Process a conversations JSON file")
    pp.add_argument("conversations", help="Path to conversations JSON")
    pp.add_argument("--store", help="Path to the JSON store (for dedup across runs)")
    pp.add_argument("--ics", help="Also write an .ics file of all events/reminders")
    pp.add_argument("--tz", help="IANA timezone (default America/Los_Angeles)")
    pp.add_argument("--now", help="Override 'now' (ISO 8601), for testing/demo")
    pp.add_argument("--travel-minutes", type=int, help="Global travel time in minutes")
    pp.add_argument(
        "--auto-routine",
        action="store_true",
        help="Treat confirmation/'on my way' drafts as auto-sendable",
    )
    pp.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    pp.set_defaults(func=cmd_process)

    pl = sub.add_parser("list", help="List tracked events and reminders")
    pl.add_argument("--store", required=True, help="Path to the JSON store")
    pl.set_defaults(func=cmd_list)

    pe = sub.add_parser("export-ics", help="Export the store to an .ics file")
    pe.add_argument("--store", required=True, help="Path to the JSON store")
    pe.add_argument("--out", required=True, help="Output .ics path")
    pe.set_defaults(func=cmd_export_ics)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
