"""Full HTML morning report, opened in the browser."""

import json
import logging
import webbrowser
from datetime import date
from pathlib import Path

from garmin_api.api import fetch_metrics, setup_logging

log = logging.getLogger(__name__)


def render_html(nights: list[dict], days: list[dict], compact: bool) -> str:
    template = (Path(__file__).parent / "report.html").read_text()
    data = {"nights": nights, "days": days, "compact": compact}
    return template.replace("__DATA__", json.dumps(data))


def report() -> None:
    """Build an HTML morning report of last night against the previous 7 nights, and open it."""
    setup_logging()
    nights, days = fetch_metrics()
    out = Path("data") / f"report-{date.today()}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(render_html(nights, days, compact=False))
    log.info("Report written to %s", out)
    webbrowser.open(out.resolve().as_uri())
