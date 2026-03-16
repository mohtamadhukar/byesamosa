"""CLI orchestrator for ByeSamosa pipeline.

Usage:
    python -m byesamosa.pipeline import --raw-dir data/raw/2026-02-17 [--refresh]
    python -m byesamosa.pipeline insights [--date YYYY-MM-DD] [--force]
    python -m byesamosa.pipeline serve
    python -m byesamosa.pipeline pull [--no-import]
"""

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from byesamosa.config import Settings

logger = logging.getLogger(__name__)


def cmd_import(args: argparse.Namespace, settings: Settings) -> None:
    """Import Oura CSV export into the processed JSON store.

    Args:
        args: Parsed CLI arguments. Expected attributes:
            - raw_dir (str): Path to directory containing exported CSV files.
            - refresh (bool): If True, delete existing processed data before importing.
        settings: Application settings loaded from environment.

    Side effects:
        Reads CSV files from raw_dir, writes normalized JSON to settings.data_dir/processed/,
        and recomputes baselines. Exits with code 1 if raw_dir does not exist.
    """
    from byesamosa.data.importer import import_oura_export

    raw_dir = Path(args.raw_dir)
    if not raw_dir.exists():
        print(f"Error: raw directory not found: {raw_dir}", file=sys.stderr)
        sys.exit(1)

    summary = import_oura_export(
        raw_dir=raw_dir,
        data_dir=settings.data_dir,
        refresh=args.refresh,
    )

    print("Import complete:")
    for dtype, count in summary.items():
        print(f"  {dtype}: {count}")
    print(f"  total: {sum(summary.values())}")


def cmd_insights(args: argparse.Namespace, settings: Settings) -> None:
    """Generate an AI-powered health insight for a given date.

    Args:
        args: Parsed CLI arguments. Expected attributes:
            - date (str | None): Target date in YYYY-MM-DD format. Defaults to latest day in store.
            - force (bool): If True, regenerate even if a cached insight exists.
        settings: Application settings loaded from environment.

    Side effects:
        Reads processed data from settings.data_dir, calls the Claude API to generate
        an insight, and caches the result to data/insights/. Logs estimated API cost.
        Exits with code 1 if no data is found in the store.
    """
    from byesamosa.ai.engine import (
        cache_insight,
        generate_insight,
        load_cached_insight,
        log_api_cost,
    )
    from byesamosa.data.queries import get_latest_day, get_trends, has_sleep_phases
    from byesamosa.data.store import DataStore

    store = DataStore(settings.data_dir)
    latest = get_latest_day(store)

    if not latest:
        print("Error: no data found in store. Run 'import' first.", file=sys.stderr)
        sys.exit(1)

    # Determine target date
    if args.date:
        target_date = date.fromisoformat(args.date)
    else:
        target_date = latest["day"]

    # Check cache (skip if --force)
    if not args.force:
        cached = load_cached_insight(target_date, settings.data_dir)
        if cached:
            print(f"Cached insight already exists for {target_date}. Use --force to regenerate.")
            return

    # Build context for AI
    # Load baselines
    baselines_file = store.processed_dir / "baselines.json"
    if baselines_file.exists():
        with open(baselines_file) as f:
            baselines_raw = json.load(f)
    else:
        baselines_raw = []

    from byesamosa.ai.prompts import format_baselines_for_prompt

    baselines = format_baselines_for_prompt(baselines_raw)

    # Get 7-day trends for key metrics
    trends_7d = {}
    for metric in ["sleep_score", "readiness_score", "activity_score", "average_hrv", "lowest_heart_rate"]:
        trends_7d[metric] = get_trends(store, metric, days=7)

    sleep_phases = has_sleep_phases(store)

    print(f"Generating insight for {target_date}...")
    insight = generate_insight(
        latest=latest,
        baselines=baselines,
        trends_7d=trends_7d,
        has_sleep_phases=sleep_phases,
        settings=settings,
    )

    # Cache and log
    cache_insight(insight, settings.data_dir)
    log_api_cost(settings.data_dir, datetime.now(), estimated_cost=0.05)

    print(f"Insight generated and cached for {target_date}.")
    print(f"  Reasoning steps: {len(insight.reasoning_chain)}")
    print(f"  Action items: {len(insight.actions)}")


def cmd_pull(args: argparse.Namespace, settings: Settings) -> None:
    """Pull Oura data export via Playwright browser automation and optionally import.

    Launches a Chromium browser, logs into Oura's Membership Hub using OTP
    retrieved via Gmail IMAP, and downloads the latest data export. If a new
    export is not yet ready, requests one.

    Args:
        args: Parsed CLI arguments. Expected attributes:
            - date (str | None): Download a specific export by date (YYYY-MM-DD).
            - no_import (bool): If True, download only without running the import pipeline.
        settings: Application settings loaded from environment.

    Side effects:
        Opens a browser window, connects to Gmail via IMAP for OTP retrieval,
        downloads and extracts ZIP files to data/raw/. Optionally runs the full
        import pipeline. Exits with code 1 if OURA_EMAIL is not configured.
    """
    from byesamosa.data.export_pull import pull_oura_export

    if not settings.oura_email:
        print(
            "Error: OURA_EMAIL is not set.\n"
            "Add OURA_EMAIL=your-email@example.com to your .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    raw_dir = settings.data_dir / "raw"

    target_date = date.fromisoformat(args.date) if args.date else None

    print(f"Pulling Oura export for {settings.oura_email}...")
    try:
        result = pull_oura_export(
            email=settings.oura_email,
            raw_dir=raw_dir,
            target_date=target_date,
            data_dir=settings.data_dir,
        )
    except Exception:
        logger.exception("Pull failed unexpectedly")
        raise

    if result.status == "downloaded" and result.path is not None:
        print(f"Export downloaded to {result.path}")

        if args.no_import:
            print("Skipping import (--no-import).")
            return

        from byesamosa.data.importer import import_oura_export
        summary = import_oura_export(
            raw_dir=result.path,
            data_dir=settings.data_dir,
            refresh=False,
        )
        print("Import complete:")
        for dtype, count in summary.items():
            print(f"  {dtype}: {count}")
        print(f"  total: {sum(summary.values())}")
    elif result.status == "requested":
        print("Export has been requested, try again in ~48 hours.")
    elif result.status == "processing":
        print("Export is being prepared, try again later.")
    elif result.status == "request_failed":
        print("Warning: export request may not have gone through. Try requesting manually at membership.ouraring.com/data-export")


def cmd_serve(args: argparse.Namespace, settings: Settings) -> None:
    """Launch FastAPI backend and Next.js frontend as concurrent subprocesses.

    Args:
        args: Parsed CLI arguments (no command-specific attributes used).
        settings: Application settings loaded from environment.

    Side effects:
        Starts uvicorn (FastAPI) on port 8000 and Next.js dev server on port 3000.
        Both are terminated gracefully on Ctrl+C or when either process exits.
    """
    import signal
    import subprocess

    project_root = Path(__file__).resolve().parent.parent.parent
    frontend_dir = project_root / "frontend"

    if not frontend_dir.exists():
        print(f"Error: frontend/ not found at {frontend_dir}", file=sys.stderr)
        sys.exit(1)

    procs: list[subprocess.Popen] = []

    def _shutdown(signum=None, frame=None):
        for p in procs:
            try:
                p.terminate()
            except OSError:
                pass
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("Starting FastAPI backend on http://127.0.0.1:8000")
    api_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "byesamosa.api.main:app",
            "--host", settings.host,
            "--port", str(settings.port),
            "--reload",
        ],
        cwd=str(project_root),
    )
    procs.append(api_proc)

    print("Starting Next.js frontend on http://localhost:3000")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(frontend_dir),
    )
    procs.append(frontend_proc)

    print("\nBoth servers running. Press Ctrl+C to stop.\n")

    try:
        # Wait for either process to exit
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    print(f"Process {p.args} exited with code {ret}. Shutting down...")
                    _shutdown()
                    sys.exit(ret)
            import time
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down...")
        _shutdown()


def main() -> None:
    """Entry point for the ByeSamosa CLI.

    Parses command-line arguments and dispatches to the appropriate subcommand
    handler (import, insights, pull, or serve).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        prog="byesamosa",
        description="ByeSamosa — Personal Oura Ring data analyzer",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # import subcommand
    import_parser = subparsers.add_parser(
        "import", help="Import Oura CSV export into processed store"
    )
    import_parser.add_argument(
        "--raw-dir", required=True, help="Path to directory with exported CSV files"
    )
    import_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Delete existing processed data before importing",
    )

    # insights subcommand
    insights_parser = subparsers.add_parser(
        "insights", help="Generate AI insight for a date"
    )
    insights_parser.add_argument(
        "--date",
        default=None,
        help="Target date (YYYY-MM-DD). Default: latest day in store.",
    )
    insights_parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if cached insight exists",
    )

    # pull subcommand
    pull_parser = subparsers.add_parser(
        "pull", help="Pull Oura data export via browser automation"
    )
    pull_parser.add_argument(
        "--no-import",
        action="store_true",
        help="Download export but skip importing into processed store",
    )
    pull_parser.add_argument(
        "--date",
        type=str,
        help="Download a specific export by date (YYYY-MM-DD), bypassing stale detection",
    )

    # serve subcommand
    subparsers.add_parser("serve", help="Launch FastAPI + Next.js dashboard")

    args = parser.parse_args()
    settings = Settings()

    if args.command == "import":
        cmd_import(args, settings)
    elif args.command == "insights":
        cmd_insights(args, settings)
    elif args.command == "pull":
        cmd_pull(args, settings)
    elif args.command == "serve":
        cmd_serve(args, settings)


if __name__ == "__main__":
    main()
