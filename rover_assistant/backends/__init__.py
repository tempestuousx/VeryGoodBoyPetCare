"""Pluggable calendar and reminder backends.

- :class:`~rover_assistant.backends.base.CalendarBackend` /
  :class:`~rover_assistant.backends.base.ReminderBackend` are the interfaces.
- :class:`~rover_assistant.backends.local.LocalStore` is a working, persistent
  implementation (JSON on disk) used for tests, dry runs, and offline use.
- :func:`~rover_assistant.backends.ics.export_ics` writes a standard .ics file
  you can import into Google/Apple/Outlook calendars.
- :class:`~rover_assistant.backends.google_calendar.GoogleCalendarBackend` is a
  real adapter that talks to the Google Calendar API when credentials are
  configured (imports the Google libraries lazily).
"""

from .base import CalendarBackend, ReminderBackend
from .local import LocalStore
from .ics import export_ics

__all__ = ["CalendarBackend", "ReminderBackend", "LocalStore", "export_ics"]
