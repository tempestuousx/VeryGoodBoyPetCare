import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from rover_assistant.datetime_parse import parse_when

TZ = ZoneInfo("America/Los_Angeles")
# 2026-08-22 is a Saturday.
NOW = datetime(2026, 8, 22, 8, 0, tzinfo=TZ)


class TestTimeParsing(unittest.TestCase):
    def p(self, text):
        return parse_when(text, NOW, TZ)

    def test_ampm(self):
        m = self.p("see you at 3pm")
        self.assertTrue(m.has_time)
        self.assertEqual(m.dt.hour, 15)
        self.assertFalse(m.assumed_meridiem)

    def test_ampm_with_minutes(self):
        m = self.p("how about 10:30 am")
        self.assertEqual((m.dt.hour, m.dt.minute), (10, 30))

    def test_24h(self):
        m = self.p("at 15:00")
        self.assertEqual(m.dt.hour, 15)

    def test_noon_midnight(self):
        self.assertEqual(self.p("meet at noon").dt.hour, 12)
        self.assertEqual(self.p("midnight walk").dt.hour, 0)

    def test_bare_hour_with_daypart(self):
        m = self.p("around 4 in the afternoon")
        self.assertEqual(m.dt.hour, 16)
        self.assertFalse(m.assumed_meridiem)

    def test_bare_hour_assumed(self):
        m = self.p("Saturday at 3")
        self.assertTrue(m.has_time)
        self.assertEqual(m.dt.hour, 15)
        self.assertTrue(m.assumed_meridiem)


class TestDateParsing(unittest.TestCase):
    def p(self, text):
        return parse_when(text, NOW, TZ)

    def test_tomorrow(self):
        m = self.p("tomorrow at 9am")
        self.assertEqual(m.dt.date(), datetime(2026, 8, 23).date())
        self.assertEqual(m.date_kind, "explicit")

    def test_month_day(self):
        m = self.p("August 29 at 3pm")
        self.assertEqual(m.dt.date(), datetime(2026, 8, 29).date())
        self.assertEqual(m.date_kind, "explicit")

    def test_numeric(self):
        m = self.p("9/5 at noon")
        self.assertEqual(m.dt.date(), datetime(2026, 9, 5).date())

    def test_weekday_kind(self):
        m = self.p("Sunday at 2pm")
        self.assertEqual(m.date_kind, "weekday")
        self.assertEqual(m.dt.weekday(), 6)

    def test_next_weekday(self):
        # From Saturday, "next Monday" is 9 days out (Mon of following week).
        m = self.p("next Monday at 10am")
        self.assertEqual(m.dt.date(), datetime(2026, 8, 31).date())

    def test_roll_year_past_date(self):
        m = self.p("January 5 at 9am")  # already passed in 2026
        self.assertEqual(m.dt.year, 2027)


class TestTentative(unittest.TestCase):
    def p(self, text):
        return parse_when(text, NOW, TZ)

    def test_maybe_is_tentative(self):
        self.assertTrue(self.p("maybe Saturday at 3pm").tentative)

    def test_how_about_not_tentative(self):
        self.assertFalse(self.p("how about Saturday at 3pm?").tentative)

    def test_none_when_no_datetime(self):
        self.assertIsNone(self.p("thanks so much!"))


if __name__ == "__main__":
    unittest.main()
