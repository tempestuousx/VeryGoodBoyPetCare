import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from rover_assistant.backends.ics import export_ics
from rover_assistant.backends.local import LocalStore
from rover_assistant.models import CalendarEvent, EventStatus, Reminder

TZ = ZoneInfo("America/Los_Angeles")


def sample_event(key="k1"):
    return CalendarEvent(
        title="Rover Meet & Greet — Jane",
        start=datetime(2026, 8, 29, 15, 0, tzinfo=TZ),
        end=datetime(2026, 8, 29, 15, 30, tzinfo=TZ),
        location="500 Oak St",
        notes="Client: Jane\nPet(s): Bailey",
        source_key=key,
        conversation_url="https://rover.example/c1",
    )


class TestLocalStore(unittest.TestCase):
    def test_upsert_and_find(self):
        store = LocalStore()
        ev = store.upsert_event(sample_event())
        self.assertIsNotNone(ev.id)
        self.assertIs(store.find_event("k1"), ev)

    def test_upsert_updates_in_place(self):
        store = LocalStore()
        store.upsert_event(sample_event())
        ev2 = sample_event()
        ev2.title = "Changed"
        store.upsert_event(ev2)
        self.assertEqual(len(store.list_events()), 1)
        self.assertEqual(store.find_event("k1").title, "Changed")

    def test_cancel(self):
        store = LocalStore()
        store.upsert_event(sample_event())
        self.assertTrue(store.cancel_event("k1"))
        self.assertEqual(store.find_event("k1").status, EventStatus.CANCELLED)
        self.assertFalse(store.cancel_event("missing"))

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "store.json"
            store = LocalStore(path)
            store.upsert_event(sample_event())
            store.upsert_reminder(
                Reminder(
                    text="Text client",
                    remind_at=datetime(2026, 8, 29, 14, 0, tzinfo=TZ),
                    source_key="r1",
                )
            )
            store.save()

            reopened = LocalStore(path)
            self.assertEqual(len(reopened.list_events()), 1)
            self.assertEqual(len(reopened.list_reminders()), 1)
            self.assertEqual(reopened.find_event("k1").location, "500 Oak St")


class TestICS(unittest.TestCase):
    def test_export_structure(self):
        ics = export_ics(
            [sample_event()],
            [
                Reminder(
                    text="Text Rover client to confirm meet-and-greet.",
                    remind_at=datetime(2026, 8, 29, 14, 0, tzinfo=TZ),
                    source_key="r1",
                )
            ],
        )
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("END:VCALENDAR", ics)
        self.assertIn("SUMMARY:Rover Meet & Greet", ics)
        self.assertIn("BEGIN:VALARM", ics)
        self.assertEqual(ics.count("BEGIN:VEVENT"), 2)
        # CRLF line endings per RFC 5545.
        self.assertIn("\r\n", ics)

    def test_cancelled_event_marked(self):
        ev = sample_event()
        ev.status = EventStatus.CANCELLED
        ics = export_ics([ev])
        self.assertIn("STATUS:CANCELLED", ics)


if __name__ == "__main__":
    unittest.main()
