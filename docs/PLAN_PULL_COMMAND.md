# Plan: Playwright-Based Oura Data Export (`pull` command)

## Context

ByeSamosa currently requires manual CSV download from Oura's Membership Hub. This adds a `pull` CLI subcommand that automates the browser login + export download via Playwright, with OTP automatically retrieved from Gmail via the Gmail API (read-only OAuth2 scope). Oura exports take up to 48 hours to prepare, so the command handles both "request export" and "download ready export" states.

## Files to Modify

| File | Change |
|------|--------|
| `byesamosa/pyproject.toml` | Add `playwright>=1.41.0`, `google-api-python-client>=2.0`, `google-auth-oauthlib>=1.0` |
| `byesamosa/src/byesamosa/config.py` | Add `oura_email: str = ""` to Settings |
| `byesamosa/.env.example` | Add `OURA_EMAIL=` line |
| `byesamosa/src/byesamosa/pipeline.py` | Add `pull` subcommand + `cmd_pull()` |
| `byesamosa/src/byesamosa/data/export_pull.py` | **New file** — Playwright browser automation |
| `byesamosa/src/byesamosa/data/gmail_otp.py` | **New file** — Gmail API OTP retrieval |

## Implementation Steps

- [x] **1. Add dependencies** (`pyproject.toml`)
  - Add `"playwright>=1.41.0"` to dependencies
  - Add `"google-api-python-client>=2.0"`, `"google-auth-oauthlib>=1.0"` for Gmail API

- [x] **2. Add `oura_email` to config** (`config.py`)
  - Add `oura_email: str = ""` field to `Settings` class
  - Add `OURA_EMAIL=your-email@example.com` to `.env.example`

- [x] **3. Create Gmail OTP module** (`gmail_otp.py`)
  - Gmail API with `gmail.readonly` OAuth2 scope
  - On first run: opens browser for Google OAuth consent, saves token to `data/.gmail_token.json` (git-ignored)
  - `fetch_oura_otp(timeout_seconds: int = 120) -> str`
    1. Connect to Gmail API
    2. Poll every ~5s for recent emails from Oura's sender address
    3. Extract OTP code from email body using regex
    4. Return the code string
  - `credentials.json` (Google OAuth client) stored in project root (git-ignored)

- [x] **4. Create Playwright export module** (`export_pull.py`)
  - `pull_oura_export(email: str, download_dir: Path, raw_dir: Path) -> Path | None`
  - **Stale export detection** using existing `data/raw/` folders:
    - Scan `data/raw/` for date-stamped folder names, find the latest (e.g., `2026-02-17`)
    - On the export page, parse the "Previous requests" list for each row's "Request on" date and ready status
    - **If newest ready export date > latest raw folder date** → download it
    - **If newest ready export date <= latest raw folder date** (already have it) → request a new export
    - **If no raw folders exist yet** → download the newest ready export (first run)
    - **If no ready exports at all** → request a new export
  - Login flow:
    1. Launch Chromium in **headed mode**
    2. Navigate to Oura sign-in page
    3. Dismiss cookie banner if present
    4. Fill email input, click Continue
    5. Wait for OTP page → call `fetch_oura_otp()` to get code from Gmail
    6. Fill OTP field(s) and submit
    7. Wait for authenticated redirect
    8. Navigate to data export page
  - Export handling:
    9. Parse the "Previous requests" table to get export dates + status
    10. Find latest `data/raw/YYYY-MM-DD/` folder for comparison
    11. Apply stale detection logic (see above)
    12. If downloading: click download icon, save ZIP, extract CSVs to `download_dir`, return path
    13. If requesting: click request button, print "Export requested. Run `pull` again in ~48 hours.", return `None`
  - Error handling: try/finally for `browser.close()`, catch `TimeoutError` with clear messages
  - After ZIP extraction, handle both flat and nested CSV structures

- [x] **5. Add `pull` subcommand to pipeline.py**
  - Add argparse subparser `pull` with `--no-import` flag
  - `cmd_pull()`:
    1. Validate `OURA_EMAIL` is set (exit with error if not)
    2. Create `data/raw/YYYY-MM-DD/` directory
    3. Call `pull_oura_export(email, download_dir, data_dir)`
    4. If `None` returned → "No new export ready. Export has been requested, try again in ~48 hours."
    5. If path returned and `--no-import` not set → call existing `import_oura_export()` from `importer.py`
    6. Print summary
  - Wire into argparse dispatch block

- [~] **6. Install, configure, and test**
  - `uv sync && playwright install chromium`
  - Set up Google Cloud OAuth credentials (one-time)
  - Test with a new data pull that has already been requested on Oura (should be ready to download)
  - Verify full flow: login → OTP from Gmail → download ready export → import
  - Iterate on selectors using the headed browser as needed

## Stale Export Detection

Uses existing `data/raw/` folder names (e.g., `data/raw/2026-02-17/`) as the source of truth — no extra state file.

The export page shows a "Previous requests" list:
```
🟢  Request on 02/22/2026    Available until 03/22/2026    [download icon]
🟢  Request on 02/12/2026    Available until 03/12/2026    [download icon]
```

Logic:
1. Find the latest date-stamped folder in `data/raw/` (e.g., `2026-02-17`)
2. Parse all rows from the "Previous requests" list on the export page
3. Find the newest row with a ready status (green dot)
4. **Newer than latest raw folder** → download it into `data/raw/YYYY-MM-DD/`
5. **Same or older** → request a new export
6. **No raw folders yet** → download the newest ready export (first run)

## Key Design Decisions

- **Gmail API with `gmail.readonly` scope** — OTP auto-retrieved; read-only access at API level
- **Headed browser mode** — user sees what's happening, can intervene if needed
- **Stale export detection via `data/raw/` folders** — compares export dates to existing raw folders, no extra state file
- **Stateless Playwright** — fresh browser each run, no stored cookies
- **Reuses existing import pipeline** — downloads CSVs then calls `import_oura_export()`
- **OAuth token cached** — Gmail auth only requires browser consent on first run
- **Selectors will need tuning** — confirmed during first headed test run

## One-Time Setup (for user)

1. Create a Google Cloud project and enable the Gmail API
2. Create OAuth 2.0 credentials (Desktop app type), download as `credentials.json` to project root
3. Add `OURA_EMAIL=your-email` to `.env`
4. Run `uv sync && playwright install chromium`
5. First `pull` run will open browser for Google OAuth consent

## Verification

- [ ] `pull` with no `OURA_EMAIL` → clear error message
- [ ] `pull` with no `credentials.json` → clear error about Gmail setup
- [ ] First `pull` → OAuth consent flow, then browser login + OTP auto-filled
- [ ] Export not ready → requests export, prints "try again in ~48 hours"
- [ ] New export ready → downloads ZIP, extracts CSVs to `data/raw/YYYY-MM-DD/`
- [ ] Same export already in `data/raw/` → requests new export instead of re-downloading
- [ ] Import runs automatically after download, prints record counts
- [ ] `--no-import` skips import step
- [ ] Subsequent runs reuse saved Gmail token (no OAuth prompt)
- [ ] Browser timeout → clean error message (no traceback)
