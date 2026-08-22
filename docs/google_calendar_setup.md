# Google Calendar setup

The assistant works fully offline with the local JSON store and `.ics` export.
To sync events and reminders directly into a Google Calendar, use
`GoogleCalendarBackend`.

## 1. Install the extra

```bash
pip install -e ".[google]"
```

## 2. Create OAuth credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create (or pick) a project and enable the **Google Calendar API**.
3. Under **APIs & Services → Credentials**, create an **OAuth client ID** of
   type **Desktop app**.
4. Download the client secret JSON (e.g. `client_secret.json`).

## 3. Authorize once and cache a token

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0)
with open("token.json", "w") as f:
    f.write(creds.to_json())
```

`token.json` and `client_secret.json` are already in `.gitignore` — never
commit them.

## 4. Point the engine at Google Calendar

```python
from google.oauth2.credentials import Credentials
from rover_assistant.backends.google_calendar import GoogleCalendarBackend
from rover_assistant.engine import AssistantEngine
from rover_assistant.ingest import load_conversations
from rover_assistant.config import Config

SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = Credentials.from_authorized_user_file("token.json", SCOPES)

cal = GoogleCalendarBackend(calendar_id="primary", credentials=creds)

cfg = Config(timezone="America/Los_Angeles")
engine = AssistantEngine(calendar=cal, reminders=cal, config=cfg)

for conv in load_conversations("examples/sample_conversations.json", cfg.tz()):
    result = engine.process(conv)
    for line in result.summary_lines():
        print(line)
```

## Dedup

Each event stores its `source_key` in
`extendedProperties.private.source_key`. The backend looks events up by that
key, so re-processing a conversation updates the existing event instead of
creating a duplicate — the same guarantee the local store gives.

## Reminders

Reminders are written as short timed events with a popup override at the
reminder time. If you'd rather use Google Tasks or a push service, implement
the `ReminderBackend` interface (`find_reminder` / `upsert_reminder` /
`cancel_reminder` / `list_reminders`) and pass it as `reminders=` to the engine.
