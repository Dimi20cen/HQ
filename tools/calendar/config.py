import os
from pathlib import Path
from urllib.parse import quote_plus

SCOPES = ["https://www.googleapis.com/auth/calendar"]

ROOT_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CALENDAR_DB_PATH", str(ROOT_DIR / "calendar.db")))

SYNC_INTERVAL_SECONDS = max(int(os.getenv("CALENDAR_SYNC_INTERVAL_SECONDS", "300")), 15)
SYNC_MAX_BACKOFF_SECONDS = max(
    int(os.getenv("CALENDAR_SYNC_MAX_BACKOFF_SECONDS", "1800")),
    SYNC_INTERVAL_SECONDS,
)

DEFAULT_EMBED_CAL_ID = "en.usa#holiday@group.v.calendar.google.com"
EMBED_CAL_ID = os.getenv("CALENDAR_ID", DEFAULT_EMBED_CAL_ID)
EMBED_TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "America/New_York")

API_DEFAULT_CAL_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:9010/auth/callback")


def parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


AUTO_SYNC_ENABLED = parse_bool(os.getenv("CALENDAR_AUTO_SYNC_ENABLED"), True)

CAL_URL = (
    f"https://calendar.google.com/calendar/embed?"
    f"src={quote_plus(EMBED_CAL_ID)}&ctz={quote_plus(EMBED_TIMEZONE)}"
    "&mode=AGENDA&showNav=0&showDate=0&showPrint=0&showTabs=0&showCalendars=0&showTitle=0"
    "&bgcolor=%23ffffff"
)
