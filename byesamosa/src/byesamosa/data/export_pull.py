"""Playwright-based Oura data export automation.

Automates browser login to Oura's Membership Hub, handles OTP via Gmail API,
and downloads/requests data exports with stale detection.
"""

import re
import shutil
import time
import zipfile
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from byesamosa.data.gmail_otp import fetch_oura_otp

OURA_EXPORT_URL = "https://membership.ouraring.com/data-export"


def _get_latest_raw_date(raw_dir: Path) -> date | None:
    """Find the latest date-stamped folder in data/raw/."""
    if not raw_dir.exists():
        return None

    dates: list[date] = []
    for folder in raw_dir.iterdir():
        if folder.is_dir():
            try:
                dates.append(date.fromisoformat(folder.name))
            except ValueError:
                continue

    return max(dates) if dates else None


def _parse_export_rows(page) -> list[dict]:
    """Parse the 'Previous requests' list on the export page.

    Each row is a div with data-status attribute containing an h3 with
    "Request on MM/DD/YYYY" and optionally a download button.

    Returns a list of dicts with keys: date, ready (bool), row_index.
    """
    rows = []
    # Each export row is a div with data-status attribute
    row_elements = page.locator("[data-status]").all()

    for i, row in enumerate(row_elements):
        status = row.get_attribute("data-status")
        text = row.inner_text()

        match = re.search(r"Request on (\d{2}/\d{2}/\d{4})", text)
        if match:
            date_str = match.group(1)
            parsed_date = datetime.strptime(date_str, "%m/%d/%Y").date()
            is_ready = status == "ready"

            rows.append({
                "date": parsed_date,
                "ready": is_ready,
                "index": i,
            })

    return rows


def _dismiss_cookie_banner(page) -> None:
    """Dismiss cookie consent banner if present."""
    try:
        # OneTrust cookie banner on membership.ouraring.com
        accept_btn = page.locator("#onetrust-accept-btn-handler").first
        if accept_btn.is_visible(timeout=3000):
            accept_btn.click()
            page.wait_for_timeout(500)
            return
    except (PlaywrightTimeout, Exception):
        pass
    try:
        accept_btn = page.locator("button:has-text('Accept'), button:has-text('Got it'), button:has-text('OK')").first
        if accept_btn.is_visible(timeout=1000):
            accept_btn.click()
            page.wait_for_timeout(500)
    except (PlaywrightTimeout, Exception):
        pass


def _login(page, email: str) -> None:
    """Login to Oura via the membership hub sign-in."""
    page.wait_for_load_state("load")
    page.goto(OURA_EXPORT_URL, wait_until="networkidle")

    _dismiss_cookie_banner(page)

    # Fill email and submit
    email_input = page.locator("input[type='email'], input[name='email']").first
    email_input.fill(email)

    continue_btn = page.locator("button:has-text('Continue'), button[type='submit']").first
    continue_btn.click()

    # Oura shows a "Send code" page — click it to trigger the OTP email
    send_code_btn = page.locator("button:has-text('Send code')").first
    otp_requested_at = time.time()
    send_code_btn.click(timeout=15000)
    print("Clicked 'Send code' — OTP email should arrive shortly.")

    # Wait for the OTP input page to load
    page.wait_for_selector("#otp-code", timeout=15000)

    # Fetch OTP from Gmail — only accept emails after we clicked Send code
    otp = fetch_oura_otp(sent_after=otp_requested_at)

    # Fill the OTP input and submit
    page.fill("#otp-code", otp)
    page.locator("#submit-button").click()

    # Wait for redirect after OTP submit
    for i in range(30):
        page.wait_for_timeout(1000)
        if "/authn/" not in page.url:
            break
    if "/authn/" in page.url:
        # Still on auth — OTP may have been wrong or expired
        body_text = page.inner_text("body")
        print(f"Warning: still on auth page. Page text: {body_text[:200]}")
        raise PlaywrightTimeout("Login did not complete — OTP may have expired")


def pull_oura_export(
    email: str, raw_dir: Path, target_date: date | None = None,
) -> Path | None:
    """Automate Oura export download via Playwright.

    Args:
        email: Oura account email address.
        raw_dir: The data/raw/ directory for stale detection and download.
        target_date: If set, download this specific export (bypass stale detection).

    Returns:
        Path to the extracted CSV directory (data/raw/YYYY-MM-DD/),
        or None if an export was requested (not yet ready).
        The folder name uses the export's date from the Oura page.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()

            # Login (goes to export URL which triggers auth redirect)
            _login(page, email)

            # After login we land on the hub — click "Export data" link
            if "/data-export" not in page.url:
                export_link = page.locator("a:has-text('Export'), a:has-text('export'), a[href*='data-export']").first
                export_link.click(timeout=10000)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)

            print(f"Export page: {page.url}")

            # Parse existing exports
            export_rows = _parse_export_rows(page)
            latest_raw = _get_latest_raw_date(raw_dir)

            # Find newest ready export
            ready_rows = [r for r in export_rows if r["ready"]]
            ready_rows.sort(key=lambda r: r["date"], reverse=True)

            if target_date is not None:
                # Download a specific export by date
                match = [r for r in ready_rows if r["date"] == target_date]
                if match:
                    print(f"Downloading requested export from {target_date}.")
                    export_dir = raw_dir / match[0]["date"].isoformat()
                    return _download_export(page, match[0], export_dir)
                else:
                    available = [r["date"].isoformat() for r in ready_rows]
                    print(f"No ready export for {target_date}. Available: {available}")
                    return None

            should_download = False
            target_row = None

            if ready_rows:
                newest_ready = ready_rows[0]

                if latest_raw is None:
                    should_download = True
                    target_row = newest_ready
                    print(f"First run. Downloading export from {newest_ready['date']}.")
                elif newest_ready["date"] > latest_raw:
                    should_download = True
                    target_row = newest_ready
                    print(f"New export available ({newest_ready['date']} > {latest_raw}). Downloading.")
                else:
                    print(f"Latest export ({newest_ready['date']}) already imported ({latest_raw}). Requesting new export.")
            else:
                print("No ready exports found. Requesting new export.")

            if should_download and target_row is not None:
                export_dir = raw_dir / target_row["date"].isoformat()
                return _download_export(page, target_row, export_dir)
            else:
                _request_new_export(page)
                return None

        except PlaywrightTimeout as e:
            print(f"Browser operation timed out: {e}")
            print("Try running the command again. If the issue persists, check your internet connection.")
            return None
        finally:
            browser.close()


def _download_export(page, target_row: dict, download_dir: Path) -> Path:
    """Download a ready export ZIP and extract CSVs directly into download_dir."""
    download_dir.mkdir(parents=True, exist_ok=True)
    # Click the download button (aria-label="Download data") for the target row
    download_buttons = page.locator("button[aria-label='Download data']").all()

    if target_row["index"] < len(download_buttons):
        btn = download_buttons[target_row["index"]]
    elif download_buttons:
        btn = download_buttons[0]
    else:
        raise RuntimeError("Could not find download button on export page.")

    with page.expect_download(timeout=120000) as download_info:
        btn.click()

    download = download_info.value
    zip_path = download_dir / download.suggested_filename
    download.save_as(str(zip_path))
    print(f"Downloaded: {zip_path.name}")

    # Extract ZIP directly into download_dir (CSVs at top level)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(download_dir)

    # Flatten nested directories — move CSVs to top level
    _flatten_csvs(download_dir)

    # Remove the ZIP after extraction
    zip_path.unlink()

    print(f"Extracted CSVs to {download_dir}")
    return download_dir


def _flatten_csvs(target_dir: Path) -> None:
    """Move CSV files from nested subdirectories to the top level and remove subdirs."""
    for csv_file in target_dir.rglob("*.csv"):
        if csv_file.parent != target_dir:
            dest = target_dir / csv_file.name
            if not dest.exists():
                shutil.move(str(csv_file), str(dest))

    # Remove all subdirectories
    for sub in target_dir.iterdir():
        if sub.is_dir():
            shutil.rmtree(sub)


def _request_new_export(page) -> None:
    """Click the button to request a new data export."""
    # Dismiss cookie banner first — it may overlay the button
    _dismiss_cookie_banner(page)

    request_btn = page.locator("button:has-text('Request your data')").first

    try:
        request_btn.scroll_into_view_if_needed()
        request_btn.click(timeout=10000)
        page.wait_for_timeout(2000)
        print("Export requested. Run `pull` again in ~48 hours.")
    except PlaywrightTimeout:
        # Try force click as fallback
        try:
            request_btn.click(force=True)
            page.wait_for_timeout(2000)
            print("Export requested. Run `pull` again in ~48 hours.")
        except Exception:
            print("Could not find the export request button. The page layout may have changed.")
            print("Please request the export manually at: https://membership.ouraring.com/data-export")
