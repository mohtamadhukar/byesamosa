# Fix: Harden Oura pull — wait for page, log state, handle processing exports, verify requests

## Context

A pull said "requested new data" but nothing was actually requested on Oura. A subsequent pull downloaded the old March 5th export. Exact root cause unclear, but the automation has several gaps: no wait for dynamic content, no visibility into what it sees, no processing-export awareness, and no verification that requests go through.

## Changes

### File: `src/byesamosa/data/export_pull.py`

**1. Wait for export rows to render before parsing** (after line 215)

Currently, if the URL already contains `/data-export` after login, the code skips the settle wait and parses immediately. The export page loads rows dynamically — they may not be in the DOM yet.

- After confirming we're on the export page, **always** wait for at least one `[data-status]` element to appear (with a reasonable timeout, e.g. 10s)
- Fallback: if no rows appear after timeout, log a warning and proceed (the page may genuinely have no exports)

```python
# Wait for export rows to render (dynamic content)
try:
    page.wait_for_selector("[data-status]", timeout=ELEMENT_WAIT_MS)
except PlaywrightTimeout:
    print("Warning: no export rows found on page after waiting.")
```

**2. Log what the Oura page shows + persist to pull history** (after `_parse_export_rows`)

Print a summary to stdout AND append to `data/logs/pull_history.json`:

```python
# Print summary
ready = [r for r in export_rows if r["ready"]]
processing = [r for r in export_rows if not r["ready"]]
ready_dates = ", ".join(r["date"].strftime("%m/%d") for r in ready)
proc_dates = ", ".join(r["date"].strftime("%m/%d") for r in processing)
print(f"Found {len(export_rows)} exports: {len(ready)} ready ({ready_dates}), {len(processing)} processing ({proc_dates})")
```

Add a `_log_pull` helper that appends a JSON entry to `data/logs/pull_history.json` (create if missing). Called at the end of `pull_oura_export` with the final result. Each entry:

```json
{
  "timestamp": "2026-03-16T09:18:38-05:00",
  "exports_found": {"ready": ["2026-03-05", "2026-03-02"], "processing": []},
  "latest_raw": "2026-03-02",
  "action": "downloaded",
  "export_date": "2026-03-05",
  "message": "New export available (2026-03-05 > 2026-03-02). Downloading."
}
```

The `_log_pull` helper takes `raw_dir` (to locate `data/logs/`) and the `PullResult` fields. It reads the existing JSON array, appends, and writes back.

**3. Check for processing exports before requesting** (update decision logic, lines 237-261)

Add processing-export awareness:

```python
processing_rows = [r for r in export_rows if not r["ready"]]
processing_rows.sort(key=lambda r: r["date"], reverse=True)
```

Updated decision table:

| Scenario | Action |
|----------|--------|
| Newest ready > latest_raw | Download (unchanged) |
| Newest ready ≤ latest_raw AND processing exists | "Export from {date} is being prepared — check back later." Return `PullResult(path=None, status="processing")`. Do NOT request another. |
| Newest ready ≤ latest_raw AND no processing | Request new export |
| No ready exports AND processing exists | "Export from {date} is being prepared." Return `PullResult(path=None, status="processing")` |
| No ready exports AND no processing | Request new export |

**4. Verify request actually worked** (in `_request_new_export`)

After clicking "Request your data" and waiting, re-parse the export rows. Check if a new processing entry appeared compared to the pre-click state. Log the result:

```python
def _request_new_export(page, pre_rows: list[dict]) -> bool:
    """Click 'Request your data' and verify it worked. Returns True if confirmed."""
    # ... existing click logic ...

    # Re-parse and verify
    post_rows = _parse_export_rows(page)
    new_processing = [r for r in post_rows if not r["ready"] and r not in pre_rows]
    if new_processing:
        print(f"Confirmed: new export requested (processing, date {new_processing[0]['date']}).")
        return True
    else:
        print("Warning: clicked 'Request your data' but no new processing export appeared. The request may not have gone through.")
        return False
```

**5. Add `PullResult` dataclass** (top of file)

Replace the `Path | None` return type with a structured result so pipeline.py can differentiate outcomes:

```python
@dataclass
class PullResult:
    path: Path | None          # Extracted CSV dir, or None
    status: str                # "downloaded" | "requested" | "processing" | "request_failed"
    message: str               # Human-readable explanation
```

### File: `src/byesamosa/pipeline.py`

**6. Use `PullResult` for differentiated messaging** (lines 168-182)

Update `cmd_pull` to use the new return type and print distinct messages:

- `downloaded` → proceed to import as before
- `requested` → "Export has been requested, try again in ~48 hours."
- `processing` → "Export from {date} is being prepared, try again later."
- `request_failed` → "Warning: export request may not have gone through. Try requesting manually at membership.ouraring.com/data-export"

The frontend PullButton detects status via string matching on output, so the distinct messages will naturally flow through.

### File: `frontend/components/PullButton.tsx`

**7. Handle "processing" and "request_failed" statuses** (line 33)

Add detection for the new messages:

- `"is being prepared"` in output → show "Processing" button state + "Export is being prepared — check back later"
- `"request may not have gone through"` in output → show as failed with the warning message
- Keep existing `"Export has been requested"` detection for confirmed requests

## Files to modify
- `src/byesamosa/data/export_pull.py` — wait for rows, logging, processing awareness, verify request, PullResult dataclass
- `src/byesamosa/pipeline.py` — use PullResult, differentiated messages
- `frontend/components/PullButton.tsx` — detect processing/failed statuses

## Verification
- [ ] `uv run pytest tests/` — no regressions
- [ ] Manual: `uv run python -m byesamosa.pipeline pull` — verify log shows export summary line
- [ ] Frontend: pull button shows correct state for each scenario
