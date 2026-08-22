import unittest

from rover_assistant.extraction import RuleBasedExtractor
from rover_assistant.models import CommitmentType, Confidence, Sender

from .helpers import NOW, TZ, conversation, msg


class TestExtraction(unittest.TestCase):
    def setUp(self):
        self.ex = RuleBasedExtractor(TZ)

    def _types(self, conv):
        return {c.type for c in self.ex.extract(conv, NOW)}

    def test_confirmed_meet_greet(self):
        conv = conversation(
            messages=[
                msg("client", "Can we do a meet and greet before booking?", 0),
                msg("me", "How about Saturday August 29 at 3pm?", 1),
                msg("client", "Saturday at 3pm works great, see you then!", 2),
            ]
        )
        cs = self.ex.extract(conv, NOW)
        mg = [c for c in cs if c.type == CommitmentType.MEET_AND_GREET_CONFIRMED]
        self.assertEqual(len(mg), 1)
        # Echo of the vague "Saturday" must not overwrite the precise Aug 29.
        self.assertEqual(mg[0].when.date().isoformat(), "2026-08-29")
        self.assertEqual(mg[0].confidence, Confidence.CONFIRMED)

    def test_tentative_is_proposed_not_confirmed(self):
        conv = conversation(
            messages=[msg("client", "Maybe Saturday could work for a meet and greet?", 0)]
        )
        types = self._types(conv)
        self.assertIn(CommitmentType.MEET_AND_GREET_PROPOSED, types)
        self.assertNotIn(CommitmentType.MEET_AND_GREET_CONFIRMED, types)

    def test_reschedule_uses_latest_time(self):
        conv = conversation(
            messages=[
                msg("me", "How about a meet and greet Saturday August 29 at 3pm?", 0),
                msg("client", "Sounds good, see you then!", 1),
                msg("client", "Actually can we do August 29 at 5pm instead?", 2),
                msg("me", "Sure, 5pm on the 29th works, confirmed!", 3),
            ]
        )
        cs = self.ex.extract(conv, NOW)
        mg = [c for c in cs if c.type == CommitmentType.MEET_AND_GREET_CONFIRMED][0]
        self.assertEqual(mg.when.hour, 17)

    def test_booking_confirmed_with_range(self):
        conv = conversation(
            service="Drop-In Visit",
            messages=[
                msg("client", "Your booking is confirmed! Drop-In Visit on September 5 from 12pm to 12:30pm.", 0)
            ],
        )
        cs = self.ex.extract(conv, NOW)
        b = [c for c in cs if c.type == CommitmentType.BOOKING_CONFIRMED][0]
        self.assertEqual(b.when.hour, 12)
        self.assertIsNotNone(b.end)
        self.assertEqual(b.end.minute, 30)

    def test_followup_detected(self):
        conv = conversation(
            messages=[
                msg("client", "Can you walk Rex next week?", 0),
                msg("me", "I'll text you tomorrow with what works!", 1),
            ]
        )
        cs = self.ex.extract(conv, NOW)
        f = [c for c in cs if c.type == CommitmentType.FOLLOW_UP_COMMITMENT]
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].made_by, Sender.ME)
        self.assertIsNotNone(f[0].when)

    def test_cancellation(self):
        conv = conversation(
            messages=[
                msg("me", "Meet and greet Saturday August 29 at 3pm, confirmed!", 0),
                msg("client", "So sorry, I need to cancel our meet and greet.", 1),
            ]
        )
        types = self._types(conv)
        self.assertIn(CommitmentType.CANCELLATION, types)

    def test_client_confirm_request(self):
        conv = conversation(
            messages=[msg("client", "Hey, are we still on for tomorrow? Please confirm.", 0)]
        )
        types = self._types(conv)
        self.assertIn(CommitmentType.CLIENT_CONFIRM_REQUEST, types)


if __name__ == "__main__":
    unittest.main()
