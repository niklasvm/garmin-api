"""Compact morning report rendered to a PNG and sent to Telegram."""

import logging
import os
from datetime import date
from pathlib import Path
from typing import Annotated

import requests
import typer
from playwright.sync_api import sync_playwright

from garmin_api.api import fetch_metrics, setup_logging
from garmin_api.report import render_html

log = logging.getLogger(__name__)


def render_png(nights: list[dict], days: list[dict], path: Path) -> None:
    """Screenshot the compact HTML report to a PNG."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # Phone width at 3x scale keeps the text sharp
        page = browser.new_page(
            viewport={"width": 480, "height": 800}, device_scale_factor=3
        )
        page.set_content(
            render_html(nights, days, compact=True), wait_until="networkidle"
        )
        page.screenshot(path=path, full_page=True)
        browser.close()


def message(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Save the image without sending it."),
    ] = False,
) -> None:
    """Send the morning summary to Telegram as a single image."""
    setup_logging()
    nights, days = fetch_metrics()
    image = Path("data") / f"message-{date.today()}.png"
    image.parent.mkdir(exist_ok=True)
    render_png(nights, days, image)
    caption = f"Morning report, {date.today():%a %d %b}"

    token, chat_id = (
        os.environ.get("TELEGRAM_BOT_TOKEN"),
        os.environ.get("TELEGRAM_CHAT_ID"),
    )
    if dry_run or not token or not chat_id:
        log.info("Image saved to %s", image)
        if not dry_run:
            log.warning(
                "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to send it."
            )
        return
    try:
        with image.open("rb") as photo:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": photo},
                timeout=30,
            )
        response.raise_for_status()
    except requests.RequestException as e:
        # requests puts the URL, which contains the bot token, in its error messages.
        # Re-raise with only the status and Telegram's description, and drop the original.
        status = e.response.status_code if e.response is not None else "no response"
        detail = e.response.text[:200] if e.response is not None else type(e).__name__
        raise RuntimeError(f"Telegram sendPhoto failed ({status}): {detail}") from None
    log.info("Sent to Telegram")


def message_cli() -> None:
    typer.run(message)
