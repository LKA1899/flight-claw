import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright

from app.crawler.browser_engine import BrowserProfile, launch_persistent_browser_context
from app.crawler.ctrip import (
    GOTO_TIMEOUT_MS,
    _build_list_url,
    _build_roundtrip_list_url,
    _classify_page_text,
    _page_visible_text,
    _save_snapshot,
    _wait_for_result_or_fail,
)
from app.crawler.xhr_capture import XhrCapture
from app.db import create_all
from app.services.settings_service import get_headless
from app.constants import TRIP_ONE_WAY, TRIP_ROUND_TRIP


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Ctrip result page XHR capture.")
    parser.add_argument("--from-city", required=True)
    parser.add_argument("--to-city", required=True)
    parser.add_argument("--depart-date", required=True)
    parser.add_argument("--return-date")
    parser.add_argument("--task-id", type=int, default=0)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    create_all()
    task = type(
        "ProbeTask",
        (),
        {
            "from_city": args.from_city,
            "from_airports": None,
            "to_city": args.to_city,
            "to_airports": None,
            "depart_date": date.fromisoformat(args.depart_date),
            "return_date": date.fromisoformat(args.return_date) if args.return_date else None,
        },
    )
    trip_type = TRIP_ROUND_TRIP if args.return_date else TRIP_ONE_WAY
    url = _build_roundtrip_list_url(task) if trip_type == TRIP_ROUND_TRIP else _build_list_url(task)
    task_id = args.task_id or 999999

    with sync_playwright() as playwright:
        profile = BrowserProfile.from_settings(headless=False if args.headed else get_headless())
        browser, profile_mode, profile_dir = launch_persistent_browser_context(playwright, task_id=task_id, profile=profile)
        page = browser.pages[0] if browser.pages else browser.new_page()
        capture = XhrCapture(
            task_id=task_id,
            stage="probe_ctrip_result",
            enabled=True,
            pattern=profile.capture_xhr_pattern,
        )
        capture.attach(page)
        page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
        try:
            _wait_for_result_or_fail(page, task_id=None)
        finally:
            screenshot_path, text_path = _save_snapshot(page, task_id, label="probe_ctrip_result")
            xhr_path = capture.finalize()
            text = _page_visible_text(page)
            state = _classify_page_text(page) or "RESULT"
            print(
                {
                    "state": state,
                    "url": page.url,
                    "profile_mode": profile_mode,
                    "profile_dir": profile_dir,
                    "screenshot_path": screenshot_path,
                    "text_path": text_path,
                    "visible_text_length": len(text),
                    "xhr_path": xhr_path,
                    "xhr_count": capture.count,
                }
            )
            browser.close()


if __name__ == "__main__":
    main()
