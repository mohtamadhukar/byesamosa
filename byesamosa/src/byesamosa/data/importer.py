"""Import orchestrator for Oura CSV exports.

Parses raw CSVs, upserts into processed JSON store, and recomputes baselines.
"""

import logging
import shutil
from pathlib import Path

from byesamosa.data.parser import parse_oura_export
from byesamosa.data.queries import compute_baselines
from byesamosa.data.store import DataStore

logger = logging.getLogger(__name__)


def import_oura_export(
    raw_dir: Path, data_dir: Path, refresh: bool = False
) -> dict:
    """Import an Oura CSV export into the processed JSON store.

    Args:
        raw_dir: Path to directory containing the exported CSV files.
        data_dir: Base data directory (contains processed/, insights/, etc.).
        refresh: If True, delete existing processed JSONs before inserting.

    Returns:
        Summary dict with record counts per type.
    """
    raw_dir = Path(raw_dir)
    data_dir = Path(data_dir)
    store = DataStore(data_dir)

    # 1. Optionally wipe processed data for a clean import
    if refresh:
        logger.info("Refresh mode: clearing processed data")
        for json_file in store.processed_dir.glob("*.json"):
            json_file.unlink()

    # 2. Parse CSV files
    logger.info("Parsing Oura export from %s", raw_dir)
    result = parse_oura_export(raw_dir)

    # 3. Upsert into JSON store
    logger.info("Upserting parsed records into store")
    store.upsert_sleep(result.sleep)
    store.upsert_readiness(result.readiness)
    store.upsert_activity(result.activity)
    store.upsert_sleep_phases(result.sleep_phases)
    store.upsert_stress(result.stress)
    store.upsert_spo2(result.spo2)
    store.upsert_cardiovascular_age(result.cardiovascular_age)
    store.upsert_workouts(result.workouts)
    store.upsert_resilience(result.resilience)

    # 4. Recompute baselines
    logger.info("Recomputing baselines")
    compute_baselines(store)

    summary = {
        "sleep": len(result.sleep),
        "readiness": len(result.readiness),
        "activity": len(result.activity),
        "stress": len(result.stress),
        "spo2": len(result.spo2),
        "cardiovascular_age": len(result.cardiovascular_age),
        "workouts": len(result.workouts),
        "resilience": len(result.resilience),
        "sleep_phases": len(result.sleep_phases),
    }
    total = sum(summary.values())
    logger.info("Import complete: %d total records", total)

    return summary
