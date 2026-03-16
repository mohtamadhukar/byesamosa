"""Playwright-based Oura data export automation.

Automates browser login to Oura's Membership Hub, handles OTP via Gmail API,
and downloads/requests data exports with stale detection.
"""

import json
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass
class PullResult:
    path: Path | None          # Extracted CSV dir, or None
    status: str                # "downloaded" | "requested" | "processing" | "request_failed"
    message: str               # Human-readable explanation


def _pull_dir_name(export_date: date) -> str:
    """Build a timestamped directory name: YYYY-MM-DDThh-mm-ssTZ."""
    now = datetime.now()
    tz_abbr = time.strftime("%Z")
    return f"{export_date.isoformat()}T{now.strftime('%H-%M-%S')}{tz_abbr}"

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from byesamosa.data.gmail_otp import fetch_oura_otp

OURA_EXPORT_URL = "https://membership.ouraring.com/data-export"

# --- Timeout constants (milliseconds) ---
NAV_TIMEOUT_MS = 30_000        # Page navigation / networkidle
ELEMENT_WAIT_MS = 10_000       # Waiting for an element to appear or become visible
OTP_FLOW_TIMEOUT_MS = 15_000   # OTP send-code click and input field wait
DOWNLOAD_TIMEOUT_MS = 120_000  # Large ZIP download from Oura
COOKIE_BANNER_MS = 3_000       # Cookie consent banner visibility check
COOKIE_BANNER_ALT_MS = 1_000   # Fallback cookie banner check

# --- Sleep constants (seconds) ---
# Brief pause after dismissing cookie banners so the DOM settles
COOKIE_DISMISS_PAUSE_S = 0.5
# Pause after navigating to export page to let dynamic content render
EXPORT_PAGE_SETTLE_S = 3
# Pause after clicking an export-related button to let server respond
BUTTON_RESPONSE_PAUSE_S = 2
# Polling interval while waiting for OTP redirect to complete
OTP_REDIRECT_POLL_S = 1
# Maximum number of OTP redirect polling iterations
OTP_REDIRECT_MAX_POLLS = 30


def _get_latest_raw_date(raw_dir: Path) -> date | None:
    """Find the latest date-stamped folder in data/raw/.

    Supports both legacy "YYYY-MM-DD" and timestamped "YYYY-MM-DDThh-mm-ssTZ" names.
    """
    if not raw_dir.exists():
        return None

    dates: list[date] = []
    for folder in raw_dir.iterdir():
        if folder.is_dir():
            try:
                dates.append(date.fromisoformat(folder.name[:10]))
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
        if accept_btn.is_visible(timeout=COOKIE_BANNER_MS):
            accept_btn.click(timeout=ELEMENT_WAIT_MS)
            page.wait_for_timeout(int(COOKIE_DISMISS_PAUSE_S * 1000))
            return
    except (PlaywrightTimeout, PlaywrightError):
        pass
    try:
        accept_btn = page.locator("button:has-text('Accept'), button:has-text('Got it'), button:has-text('OK')").first
        if accept_btn.is_visible(timeout=COOKIE_BANNER_ALT_MS):
            accept_btn.click(timeout=ELEMENT_WAIT_MS)
            page.wait_for_timeout(int(COOKIE_DISMISS_PAUSE_S * 1000))
    except (PlaywrightTimeout, PlaywrightError):
        pass


def _login(page, email: str) -> None:
    """Login to Oura via the membership hub sign-in."""
    page.wait_for_load_state("load", timeout=NAV_TIMEOUT_MS)
    page.goto(OURA_EXPORT_URL, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)

    _dismiss_cookie_banner(page)

    # Fill email and submit
    email_input = page.locator("input[type='email'], input[name='email']").first
    email_input.fill(email, timeout=ELEMENT_WAIT_MS)

    continue_btn = page.locator("button:has-text('Continue'), button[type='submit']").first
    continue_btn.click(timeout=ELEMENT_WAIT_MS)

    # Oura shows a "Send code" page — click it to trigger the OTP email
    send_code_btn = page.locator("button:has-text('Send code')").first
    otp_requested_at = time.time()
    send_code_btn.click(timeout=OTP_FLOW_TIMEOUT_MS)
    print("Clicked 'Send code' — OTP email should arrive shortly.")

    # Wait for the OTP input page to load
    page.wait_for_selector("#otp-code", timeout=OTP_FLOW_TIMEOUT_MS)

    # Fetch OTP from Gmail — only accept emails after we clicked Send code
    otp = fetch_oura_otp(sent_after=otp_requested_at)

    # Fill the OTP input and submit
    page.fill("#otp-code", otp, timeout=ELEMENT_WAIT_MS)
    page.locator("#submit-button").click(timeout=ELEMENT_WAIT_MS)

    # Wait for redirect after OTP submit
    for _ in range(OTP_REDIRECT_MAX_POLLS):
        page.wait_for_timeout(int(OTP_REDIRECT_POLL_S * 1000))
        if "/authn/" not in page.url:
            break
    if "/authn/" in page.url:
        # Still on auth — OTP may have been wrong or expired
        body_text = page.inner_text("body")
        print(f"Warning: still on auth page. Page text: {body_text[:200]}")
        raise PlaywrightTimeout("Login did not complete — OTP may have expired")


def _validate_download_dir(raw_dir: Path) -> None:
    """Ensure the download directory exists and is writable. Create if needed."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    if not os.access(raw_dir, os.W_OK):
        raise PermissionError(
            f"Download directory is not writable: {raw_dir}"
        )


def _load_oura_email() -> str:
    """Load OURA_EMAIL from environment, raising ValueError if not set."""
    email = os.environ.get("OURA_EMAIL", "").strip()
    if not email:
        raise ValueError(
            "OURA_EMAIL is not set. "
            "Add OURA_EMAIL=your-email@example.com to your .env file."
        )
    return email


def _log_pull(raw_dir: Path, result: PullResult, exports_found: dict, latest_raw: date | None = None) -> None:
    """Append a pull event to data/logs/pull_history.json."""
    logs_dir = raw_dir.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "pull_history.json"

    entry = {
        "timestamp": datetime.now().astimezone().isoformat(),
        "exports_found": exports_found,
        "latest_raw": latest_raw.isoformat() if latest_raw else None,
        "action": result.status,
        "export_date": result.path.name[:10] if result.path else None,
        "message": result.message,
    }

    history = []
    if log_file.exists():
        try:
            history = json.loads(log_file.read_text())
        except (json.JSONDecodeError, ValueError):
            pass

    history.append(entry)
    log_file.write_text(json.dumps(history, indent=2) + "\n")


def pull_oura_export(
    email: str, raw_dir: Path, target_date: date | None = None,
) -> PullResult:
    """Automate Oura export download via Playwright.

    Args:
        email: Oura account email address.
        raw_dir: The data/raw/ directory for stale detection and download.
        target_date: If set, download this specific export (bypass stale detection).

    Returns:
        PullResult with path to extracted CSV directory, status, and message.
    """
    _validate_download_dir(raw_dir)

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
                export_link.click(timeout=ELEMENT_WAIT_MS)
                page.wait_for_load_state("networkidle", timeout=NAV_TIMEOUT_MS)
                page.wait_for_timeout(int(EXPORT_PAGE_SETTLE_S * 1000))

            print(f"Export page: {page.url}")

            # Wait for export rows to render (dynamic content)
            try:
                page.wait_for_selector("[data-status]", timeout=ELEMENT_WAIT_MS)
            except PlaywrightTimeout:
                print("Warning: no export rows found on page after waiting.")

            # Parse existing exports
            export_rows = _parse_export_rows(page)

            ready = [r for r in export_rows if r["ready"]]
            ready.sort(key=lambda r: r["date"], reverse=True)
            processing = [r for r in export_rows if not r["ready"]]
            processing.sort(key=lambda r: r["date"], reverse=True)
            ready_dates = ", ".join(r["date"].strftime("%m/%d") for r in ready)
            proc_dates = ", ".join(r["date"].strftime("%m/%d") for r in processing)
            print(f"Found {len(export_rows)} exports: {len(ready)} ready ({ready_dates}), {len(processing)} processing ({proc_dates})")

            exports_found = {
                "ready": [r["date"].isoformat() for r in ready],
                "processing": [r["date"].isoformat() for r in processing],
            }

            latest_raw = _get_latest_raw_date(raw_dir)

            if target_date is not None:
                # Download a specific export by date
                match = [r for r in ready if r["date"] == target_date]
                if match:
                    print(f"Downloading requested export from {target_date}.")
                    export_dir = raw_dir / _pull_dir_name(match[0]["date"])
                    path = _download_export(page, match[0], export_dir)
                    result = PullResult(path=path, status="downloaded", message=f"Downloaded export from {target_date}.")
                    _log_pull(raw_dir, result, exports_found, latest_raw)
                    return result
                else:
                    available = [r["date"].isoformat() for r in ready]
                    msg = f"No ready export for {target_date}. Available: {available}"
                    print(msg)
                    result = PullResult(path=None, status="request_failed", message=msg)
                    _log_pull(raw_dir, result, exports_found, latest_raw)
                    return result

            # Auto-detection path
            if ready:
                newest_ready = ready[0]

                if latest_raw is None or newest_ready["date"] > latest_raw:
                    # Download the newest ready export
                    if latest_raw is None:
                        print(f"First run. Downloading export from {newest_ready['date']}.")
                    else:
                        print(f"New export available ({newest_ready['date']} > {latest_raw}). Downloading.")

                    export_dir = raw_dir / _pull_dir_name(newest_ready["date"])
                    path = _download_export(page, newest_ready, export_dir)
                    result = PullResult(path=path, status="downloaded", message=f"Downloaded export from {newest_ready['date']}.")
                    _log_pull(raw_dir, result, exports_found, latest_raw)
                    return result
                else:
                    # newest ready <= latest_raw
                    if processing:
                        proc_date = processing[0]["date"]
                        msg = f"Export from {proc_date} is being prepared — check back later."
                        print(msg)
                        result = PullResult(path=None, status="processing", message=msg)
                        _log_pull(raw_dir, result, exports_found, latest_raw)
                        return result
                    else:
                        print(f"Latest export ({newest_ready['date']}) already imported ({latest_raw}). Requesting new export.")
                        confirmed = _request_new_export(page, export_rows)
                        if confirmed:
                            result = PullResult(path=None, status="requested", message="Export requested. Try again in ~48 hours.")
                        else:
                            result = PullResult(path=None, status="request_failed", message="Export request may not have gone through.")
                        _log_pull(raw_dir, result, exports_found, latest_raw)
                        return result
            else:
                # No ready exports
                if processing:
                    proc_date = processing[0]["date"]
                    msg = f"Export from {proc_date} is being prepared — check back later."
                    print(msg)
                    result = PullResult(path=None, status="processing", message=msg)
                    _log_pull(raw_dir, result, exports_found, latest_raw)
                    return result
                else:
                    print("No ready exports found. Requesting new export.")
                    confirmed = _request_new_export(page, export_rows)
                    if confirmed:
                        result = PullResult(path=None, status="requested", message="Export requested. Try again in ~48 hours.")
                    else:
                        result = PullResult(path=None, status="request_failed", message="Export request may not have gone through.")
                    _log_pull(raw_dir, result, exports_found, latest_raw)
                    return result

        except PlaywrightTimeout as e:
            print(f"Browser operation timed out: {e}")
            print("Try running the command again. If the issue persists, check your internet connection.")
            result = PullResult(path=None, status="request_failed", message=str(e))
            _log_pull(raw_dir, result, {})
            return result
        except PlaywrightError as e:
            print(f"Browser error: {e}")
            result = PullResult(path=None, status="request_failed", message=str(e))
            _log_pull(raw_dir, result, {})
            return result
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

    with page.expect_download(timeout=DOWNLOAD_TIMEOUT_MS) as download_info:
        btn.click(timeout=ELEMENT_WAIT_MS)

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


def _request_new_export(page, pre_rows: list[dict]) -> bool:
    """Click 'Request your data' and verify it worked. Returns True if confirmed."""
    _dismiss_cookie_banner(page)
    request_btn = page.locator("button:has-text('Request your data')").first
    try:
        request_btn.scroll_into_view_if_needed(timeout=ELEMENT_WAIT_MS)
        request_btn.click(timeout=ELEMENT_WAIT_MS)
        page.wait_for_timeout(int(BUTTON_RESPONSE_PAUSE_S * 1000))
    except PlaywrightTimeout:
        try:
            request_btn.click(force=True, timeout=ELEMENT_WAIT_MS)
            page.wait_for_timeout(int(BUTTON_RESPONSE_PAUSE_S * 1000))
        except PlaywrightError:
            print("Could not find the export request button. The page layout may have changed.")
            return False

    # Re-parse and verify
    post_rows = _parse_export_rows(page)
    pre_processing_dates = {r["date"] for r in pre_rows if not r["ready"]}
    new_processing = [r for r in post_rows if not r["ready"] and r["date"] not in pre_processing_dates]
    if new_processing:
        print(f"Confirmed: new export requested (processing, date {new_processing[0]['date']}).")
        return True
    else:
        print("Warning: clicked 'Request your data' but no new processing export appeared.")
        return False
