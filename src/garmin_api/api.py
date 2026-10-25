"""Garmin Personal API access: an authenticated client and the metrics the reports use."""

import logging
import os
from datetime import UTC, date, datetime, timedelta

import requests
from dotenv import load_dotenv
from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
    resolve_api_key,
)
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

log = logging.getLogger(__name__)

SECRET_ENV_VARS = ("GARMIN_PERSONAL_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")


class _RedactSecrets(logging.Filter):
    """Safety net: replace any secret from the environment with *** before a log line is written."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for name in SECRET_ENV_VARS:
            if value := os.environ.get(name):
                message = message.replace(value, "***")
        record.msg, record.args = message, None
        return True


def setup_logging() -> None:
    """Log to stderr at INFO, including the Garmin library's request lines, with secrets redacted."""
    load_dotenv()
    handler = logging.StreamHandler()
    handler.addFilter(_RedactSecrets())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S")
    )
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)


def _retrying_session() -> requests.Session:
    """Session that retries rate limits (429) and transient server errors with exponential backoff."""
    retry = Retry(
        total=5,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=2,  # waits 2, 4, 8, 16, 32 s between attempts
        respect_retry_after_header=True,
        # POST is the token exchange, which is safe to repeat
        allowed_methods=["GET", "POST"],
        raise_on_status=False,  # hand the final response back so the library raises its HttpError
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def get_client() -> GarminPersonalApiClient:
    load_dotenv()

    # Exchanges the API key (GARMIN_PERSONAL_API_KEY) for a bearer token, cached under ~/.config/garmin.
    # The authenticator closes its session on exit, so the client gets its own.
    with PersonalApiAuthenticator(session=_retrying_session()) as auth:
        token = auth.obtain_token(resolve_api_key())
    return GarminPersonalApiClient(token.access_token, session=_retrying_session())


def _local_hours(ms: int) -> float:
    """Return a Garmin local epoch-ms timestamp as hours from midnight (evening negative)."""
    t = datetime.fromtimestamp(ms / 1000, UTC)
    h = t.hour + t.minute / 60
    return round(h - 24 if h >= 12 else h, 2)


def fetch_metrics() -> tuple[list[dict], list[dict]]:
    """Return the last 8 nights (ending last night) and the last 8 full days (ending yesterday).

    Resting HR goes with the nights: Garmin's value for a date is mostly set by the sleep before it,
    and it's what the watch shows that morning.
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    with get_client() as client:
        sleep = client.get_daily_sleep_summaries(today - timedelta(days=7), today)
        hrv = client.get_daily_hrv_summaries(today - timedelta(days=7), today)
        summaries = client.get_daily_summaries(yesterday - timedelta(days=7), today)

    hrv_by_date = {h["calendarDate"]: h for h in hrv.get("hrvSummaries", [])}
    rhr_by_date = {
        d["calendarDate"]: d.get("heartRate", {}).get("restingValue")
        for d in summaries.get("data", [])
    }
    nights = []
    for s in sleep:
        if s.get("sleepStartTimestampLocal") is None:
            continue
        h = hrv_by_date.get(s["calendarDate"], {})
        nights.append(
            {
                "date": s["calendarDate"],
                "bed_h": _local_hours(s["sleepStartTimestampLocal"]),
                "wake_h": _local_hours(s["sleepEndTimestampLocal"]),
                "sleep_h": round(s.get("sleepTimeSeconds", 0) / 3600, 2),
                "deep_h": round(s.get("deepSleepSeconds", 0) / 3600, 2),
                "light_h": round(s.get("lightSleepSeconds", 0) / 3600, 2),
                "rem_h": round(s.get("remSleepSeconds", 0) / 3600, 2),
                "awake_h": round(s.get("awakeSleepSeconds", 0) / 3600, 2),
                "score": s.get("sleepScores", {}).get("overall", {}).get("value"),
                "sleep_hr": s.get("avgHeartRate"),
                "rhr": rhr_by_date.get(s["calendarDate"]),
                "hrv": h.get("lastNightAvg"),
                "hrv_low": h.get("baseline", {}).get("balancedLow"),
                "hrv_high": h.get("baseline", {}).get("balancedUpper"),
            }
        )

    days = [
        {
            "date": d["calendarDate"],
            "bb_min": d.get("bodyBattery", {}).get("minValue"),
            "bb_max": d.get("bodyBattery", {}).get("maxValue"),
            "stress_avg": d.get("stress", {}).get("avgLevel"),
            "stress_max": d.get("stress", {}).get("maxLevel"),
        }
        for d in summaries.get("data", [])
        if d["calendarDate"] < today.isoformat()
    ]

    # Counts only: logs may be public (GitHub Actions), so no health values
    log.info("Fetched %d nights and %d days", len(nights), len(days))
    return sorted(nights, key=lambda r: r["date"]), sorted(
        days, key=lambda r: r["date"]
    )
