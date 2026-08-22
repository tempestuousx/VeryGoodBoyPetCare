import unittest
from datetime import timedelta

from rover_assistant.backends.local import LocalStore
from rover_assistant.config import Config
from rover_assistant.engine import AssistantEngine
from rover_assistant.models import EventStatus, MessageKind, Pet

from .helpers import NOW, conversation, msg


def make_engine(auto_routine=False, travel_minutes=None):
    store = LocalStore()
    cfg = Config()
    if travel_minutes is not None:
        cfg.default_travel_minutes = travel_minutes
    engine = AssistantEngine(
        calendar=store, reminders=store, config=cfg, auto_routine_messages=auto_routine
    )
    return engine, store


CONFIRMED_MG = [
    msg("client", "Can we do a meet and greet?", 0),
    msg("me", "How about Saturday August 29 at 3pm?", 1),
    msg("client", "Saturday at 3pm works great, see you then! We're at 500 Oak St.", 2),
]


class TestEngine(unittest.TestCase):
    def test_creates_event_and_two_reminders(self):
        engine, store = make_engine()
        conv = conversation(messages=CONFIRMED_MG, address="500 Oak St",
                            pets=[Pet(name="Bailey", species="dog")])
        result = engine.process(conv, now=NOW)
        self.assertEqual(len(result.created_events), 1)
        self.assertEqual(len(result.created_reminders), 2)
        ev = result.created_events[0]
        self.assertIn("Meet & Greet", ev.title)
        self.assertIn("Bailey", ev.title)
        self.assertEqual(ev.location, "500 Oak St")
        self.assertIn("Bailey", ev.notes)

    def test_no_duplicate_on_reprocess(self):
        engine, store = make_engine()
        conv = conversation(messages=CONFIRMED_MG)
        engine.process(conv, now=NOW)
        result2 = engine.process(conv, now=NOW)
        self.assertEqual(len(result2.created_events), 0)
        self.assertEqual(len(result2.updated_events), 1)
        self.assertEqual(len(store.list_events()), 1)

    def test_reschedule_updates_same_event(self):
        engine, store = make_engine()
        conv = conversation(cid="resc", messages=CONFIRMED_MG)
        engine.process(conv, now=NOW)
        first = store.list_events()[0].start
        conv.messages.append(
            msg("client", "Actually can we move it to August 29 at 5pm?", 5)
        )
        conv.messages.append(msg("me", "5pm on the 29th, confirmed!", 6))
        engine.process(conv, now=NOW)
        self.assertEqual(len(store.list_events()), 1)
        self.assertEqual(store.list_events()[0].start.hour, 17)
        self.assertNotEqual(store.list_events()[0].start, first)

    def test_confirm_reminder_lead_one_hour(self):
        engine, store = make_engine()
        conv = conversation(messages=CONFIRMED_MG)
        engine.process(conv, now=NOW)
        confirm = [r for r in store.list_reminders() if "confirm meet-and-greet" in r.text]
        self.assertEqual(len(confirm), 1)
        appt = store.list_events()[0].start
        self.assertEqual(appt - confirm[0].remind_at, timedelta(hours=1))

    def test_on_my_way_uses_travel_time(self):
        engine, store = make_engine(travel_minutes=40)
        conv = conversation(messages=CONFIRMED_MG)
        engine.process(conv, now=NOW)
        omw = [r for r in store.list_reminders() if "On my way" in r.text][0]
        appt = store.list_events()[0].start
        # 40 min travel + 5 min send buffer.
        self.assertEqual(appt - omw.remind_at, timedelta(minutes=45))

    def test_redundant_confirm_skipped(self):
        engine, store = make_engine()
        # A confirmed M&G for a near-future time, with a recent confirm from me.
        near = NOW + timedelta(hours=2)
        text_time = near.strftime("%-I%p").lower()
        messages = [
            msg("client", "meet and greet today?", 0),
            msg("me", f"Yes, confirmed for today at {text_time}!", 1),
        ]
        conv = conversation(cid="redund", messages=messages)
        # Add a very recent confirmation message from me (within window).
        conv.messages.append(
            type(messages[0])(sender=messages[1].sender,
                              text="Just confirming we're still on, see you soon!",
                              timestamp=near - timedelta(minutes=30))
        )
        result = engine.process(conv, now=NOW)
        confirm = [r for r in store.list_reminders() if "confirm meet-and-greet" in r.text]
        self.assertEqual(len(confirm), 0)
        self.assertTrue(any("Skipped confirmation reminder" in l for l in result.log))

    def test_tentative_creates_no_event(self):
        engine, store = make_engine()
        conv = conversation(
            messages=[msg("client", "Maybe Saturday could work for a meet and greet?", 0)]
        )
        result = engine.process(conv, now=NOW)
        self.assertEqual(len(store.list_events()), 0)
        self.assertTrue(result.flags)

    def test_cancellation_cancels_event_and_reminders(self):
        engine, store = make_engine()
        conv = conversation(cid="cancel", messages=CONFIRMED_MG)
        engine.process(conv, now=NOW)
        conv.messages.append(msg("client", "I need to cancel our meet and greet, sorry!", 7))
        engine.process(conv, now=NOW)
        ev = store.list_events()[0]
        self.assertEqual(ev.status, EventStatus.CANCELLED)
        actives = [r for r in store.list_reminders() if r.status.value == "active"]
        self.assertEqual(len(actives), 0)

    def test_booking_event_title(self):
        engine, store = make_engine()
        conv = conversation(
            cid="bk",
            service="Drop-In Visit",
            pets=[Pet(name="Milo"), Pet(name="Luna")],
            messages=[msg("client", "Your booking is confirmed for September 5 at 12pm.", 0)],
        )
        engine.process(conv, now=NOW)
        ev = store.list_events()[0]
        self.assertEqual(ev.title, "Rover — Drop-In Visit — Milo & Luna")

    def test_messages_require_approval_by_default(self):
        engine, store = make_engine(auto_routine=False)
        conv = conversation(messages=CONFIRMED_MG)
        result = engine.process(conv, now=NOW)
        self.assertTrue(all(m.requires_approval for m in result.prepared_messages))

    def test_auto_routine_marks_messages_sendable(self):
        engine, store = make_engine(auto_routine=True)
        conv = conversation(messages=CONFIRMED_MG)
        result = engine.process(conv, now=NOW)
        kinds = {m.kind for m in result.prepared_messages}
        self.assertIn(MessageKind.CONFIRMATION, kinds)
        self.assertTrue(all(not m.requires_approval for m in result.prepared_messages))

    def test_followup_creates_reminder(self):
        engine, store = make_engine()
        conv = conversation(
            cid="fu",
            messages=[
                msg("client", "Walk next week?", 0),
                msg("me", "I'll text you tomorrow!", 1),
            ],
        )
        engine.process(conv, now=NOW)
        self.assertEqual(len(store.list_reminders()), 1)


if __name__ == "__main__":
    unittest.main()
