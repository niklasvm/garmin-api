"""Ad-hoc commands for exploring what the API returns."""

import json
from datetime import date, timedelta
from pathlib import Path

from garmin_personal_api import GarminPersonalApiError

from garmin_api.api import get_client


def main() -> None:
    end = date.today()
    start = end - timedelta(days=7)

    with get_client() as client:
        print(json.dumps(client.get_user_profile_settings(), indent=2))
        print(json.dumps(client.get_daily_steps(start, end), indent=2))


def explore() -> None:
    """Save one sample response per sleep, HRV and heart rate endpoint to data/."""
    day = date.today() - timedelta(days=1)
    start = day - timedelta(days=6)
    out = Path("data")
    out.mkdir(exist_ok=True)

    with get_client() as client:
        samples = {
            "daily_sleep": lambda: client.get_daily_sleep(day),
            "daily_sleep_summaries": lambda: client.get_daily_sleep_summaries(
                start, day
            ),
            "daily_hrv": lambda: client.get_daily_hrv(day),
            "daily_hrv_summaries": lambda: client.get_daily_hrv_summaries(start, day),
            "daily_heart_rate": lambda: client.get_daily_heart_rate(day),
            "daily_summaries": lambda: client.get_daily_summaries(start, day),
        }
        for name, fetch in samples.items():
            try:
                (out / f"{name}.json").write_text(json.dumps(fetch(), indent=2))
                print(f"saved {name}")
            except GarminPersonalApiError as e:
                print(f"failed {name}: {e}")
