"""CSV parser for Oura Ring export data.

Reads semicolon-delimited CSVs with embedded JSON columns from Oura's
data export and converts them into Pydantic model instances.
"""

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Literal, Optional

from byesamosa.data.models import (
    ActivityContributors,
    DailyActivity,
    DailyCardiovascularAge,
    DailyReadiness,
    DailyResilience,
    DailySleep,
    DailySpO2,
    DailyStress,
    ReadinessContributors,
    ResilienceContributors,
    SleepContributors,
    SleepPhaseInterval,
    Workout,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

SLEEP_PHASE_MAP: dict[str, Literal["awake", "rem", "light", "deep"]] = {
    "1": "deep",
    "2": "light",
    "3": "rem",
    "4": "awake",
}


def _read_csv(path: Path) -> list[dict]:
    """Read a semicolon-delimited CSV file.

    For each cell value:
    - If it starts with '{', parse it as JSON.
    - Convert empty strings to None.

    Returns a list of dicts (one per row).
    """
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(StringIO(text), delimiter=";")
    rows: list[dict] = []
    for raw_row in reader:
        row: dict = {}
        for key, value in raw_row.items():
            if value is None or value == "":
                row[key] = None
            elif isinstance(value, str) and value.strip().startswith("{"):
                try:
                    row[key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    row[key] = value
            else:
                row[key] = value
        rows.append(row)
    return rows


def _int_or_none(val) -> Optional[int]:
    """Convert a value to int, returning None for None/empty/non-numeric."""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None
    return None


def _float_or_none(val) -> Optional[float]:
    """Convert a value to float, returning None for None/empty/non-numeric."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    return None


def _datetime_or_none(val) -> Optional[datetime]:
    """Parse an ISO-format datetime string, returning None on failure."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        val = val.strip()
        if val == "":
            return None
        try:
            return datetime.fromisoformat(val)
        except (ValueError, TypeError):
            return None
    return None


# ---------------------------------------------------------------------------
# Per-type parsers
# ---------------------------------------------------------------------------


def parse_daily_sleep(
    dailysleep_path: Path, sleepmodel_path: Path
) -> list[DailySleep]:
    """Parse daily sleep data by merging dailysleep.csv and sleepmodel.csv.

    For sleepmodel rows with the same day, prefer type=="long_sleep".
    If still multiple, pick the one with the longest total_sleep_duration.

    Score and contributors come from dailysleep.csv (matched by day).
    Raw metrics come from sleepmodel.csv.
    temperature_deviation comes from sleepmodel's readiness JSON column.
    """
    dailysleep_rows = _read_csv(dailysleep_path)
    sleepmodel_rows = _read_csv(sleepmodel_path)

    # Index dailysleep by day for quick lookup
    dailysleep_by_day: dict[str, dict] = {}
    for row in dailysleep_rows:
        day = row.get("day")
        if day:
            dailysleep_by_day[day] = row

    # Group sleepmodel rows by day, then pick best row per day
    sleepmodel_by_day: dict[str, list[dict]] = {}
    for row in sleepmodel_rows:
        day = row.get("day")
        if day:
            sleepmodel_by_day.setdefault(day, []).append(row)

    best_sleepmodel: dict[str, dict] = {}
    for day, rows in sleepmodel_by_day.items():
        # Prefer long_sleep rows
        long_sleep_rows = [r for r in rows if r.get("type") == "long_sleep"]
        candidates = long_sleep_rows if long_sleep_rows else rows

        # Among candidates, pick longest total_sleep_duration
        best = max(
            candidates,
            key=lambda r: _int_or_none(r.get("total_sleep_duration")) or 0,
        )
        best_sleepmodel[day] = best

    results: list[DailySleep] = []
    for day, sm_row in sorted(best_sleepmodel.items()):
        ds_row = dailysleep_by_day.get(day, {})

        # Parse contributors from dailysleep
        raw_contrib = ds_row.get("contributors")
        contributors: Optional[SleepContributors] = None
        if isinstance(raw_contrib, dict):
            contributors = SleepContributors(
                deep_sleep=_int_or_none(raw_contrib.get("deep_sleep")),
                efficiency=_int_or_none(raw_contrib.get("efficiency")),
                latency=_int_or_none(raw_contrib.get("latency")),
                rem_sleep=_int_or_none(raw_contrib.get("rem_sleep")),
                restfulness=_int_or_none(raw_contrib.get("restfulness")),
                timing=_int_or_none(raw_contrib.get("timing")),
                total_sleep=_int_or_none(raw_contrib.get("total_sleep")),
            )

        # Extract temperature_deviation from sleepmodel's readiness JSON
        readiness_data = sm_row.get("readiness")
        temp_dev: Optional[float] = None
        if isinstance(readiness_data, dict):
            temp_dev = _float_or_none(readiness_data.get("temperature_deviation"))

        try:
            record = DailySleep(
                day=day,
                score=_int_or_none(ds_row.get("score")),
                contributors=contributors,
                total_sleep_duration=_int_or_none(sm_row.get("total_sleep_duration")),
                rem_sleep_duration=_int_or_none(sm_row.get("rem_sleep_duration")),
                deep_sleep_duration=_int_or_none(sm_row.get("deep_sleep_duration")),
                light_sleep_duration=_int_or_none(sm_row.get("light_sleep_duration")),
                awake_time=_int_or_none(sm_row.get("awake_time")),
                efficiency=_int_or_none(sm_row.get("efficiency")),
                average_hrv=_int_or_none(sm_row.get("average_hrv")),
                lowest_heart_rate=_int_or_none(sm_row.get("lowest_heart_rate")),
                temperature_deviation=temp_dev,
                bedtime_start=_datetime_or_none(sm_row.get("bedtime_start")),
                bedtime_end=_datetime_or_none(sm_row.get("bedtime_end")),
                average_heart_rate=_int_or_none(sm_row.get("average_heart_rate")),
                average_breath=_float_or_none(sm_row.get("average_breath")),
                time_in_bed=_int_or_none(sm_row.get("time_in_bed")),
                restless_periods=_int_or_none(sm_row.get("restless_periods")),
            )
            results.append(record)
        except Exception:
            logger.warning("Failed to parse DailySleep for day=%s", day, exc_info=True)

    return results


def parse_daily_readiness(path: Path) -> list[DailyReadiness]:
    """Parse daily readiness data from dailyreadiness.csv."""
    rows = _read_csv(path)
    results: list[DailyReadiness] = []

    for row in rows:
        day = row.get("day")
        if not day:
            continue

        raw_contrib = row.get("contributors")
        contributors: Optional[ReadinessContributors] = None
        if isinstance(raw_contrib, dict):
            contributors = ReadinessContributors(
                activity_balance=_int_or_none(raw_contrib.get("activity_balance")),
                body_temperature=_int_or_none(raw_contrib.get("body_temperature")),
                hrv_balance=_int_or_none(raw_contrib.get("hrv_balance")),
                previous_day_activity=_int_or_none(
                    raw_contrib.get("previous_day_activity")
                ),
                previous_night=_int_or_none(raw_contrib.get("previous_night")),
                recovery_index=_int_or_none(raw_contrib.get("recovery_index")),
                resting_heart_rate=_int_or_none(
                    raw_contrib.get("resting_heart_rate")
                ),
                sleep_balance=_int_or_none(raw_contrib.get("sleep_balance")),
                sleep_regularity=_int_or_none(raw_contrib.get("sleep_regularity")),
            )

        try:
            record = DailyReadiness(
                day=day,
                score=_int_or_none(row.get("score")),
                contributors=contributors,
                temperature_deviation=_float_or_none(
                    row.get("temperature_deviation")
                ),
                temperature_trend_deviation=_float_or_none(
                    row.get("temperature_trend_deviation")
                ),
            )
            results.append(record)
        except Exception:
            logger.warning(
                "Failed to parse DailyReadiness for day=%s", day, exc_info=True
            )

    return results


def parse_daily_activity(path: Path) -> list[DailyActivity]:
    """Parse daily activity data from dailyactivity.csv.

    Skips the 'met' and 'class_5_min' columns (large, not needed).
    """
    rows = _read_csv(path)
    results: list[DailyActivity] = []

    for row in rows:
        day = row.get("day")
        if not day:
            continue

        raw_contrib = row.get("contributors")
        contributors: Optional[ActivityContributors] = None
        if isinstance(raw_contrib, dict):
            contributors = ActivityContributors(
                meet_daily_targets=_int_or_none(
                    raw_contrib.get("meet_daily_targets")
                ),
                move_every_hour=_int_or_none(raw_contrib.get("move_every_hour")),
                recovery_time=_int_or_none(raw_contrib.get("recovery_time")),
                stay_active=_int_or_none(raw_contrib.get("stay_active")),
                training_frequency=_int_or_none(
                    raw_contrib.get("training_frequency")
                ),
                training_volume=_int_or_none(raw_contrib.get("training_volume")),
            )

        try:
            record = DailyActivity(
                day=day,
                score=_int_or_none(row.get("score")),
                contributors=contributors,
                steps=_int_or_none(row.get("steps")),
                active_calories=_int_or_none(row.get("active_calories")),
                total_calories=_int_or_none(row.get("total_calories")),
                high_activity_time=_int_or_none(row.get("high_activity_time")),
                medium_activity_time=_int_or_none(row.get("medium_activity_time")),
                low_activity_time=_int_or_none(row.get("low_activity_time")),
                sedentary_time=_int_or_none(row.get("sedentary_time")),
                resting_time=_int_or_none(row.get("resting_time")),
                non_wear_time=_int_or_none(row.get("non_wear_time")),
                equivalent_walking_distance=_int_or_none(
                    row.get("equivalent_walking_distance")
                ),
                inactivity_alerts=_int_or_none(row.get("inactivity_alerts")),
                target_calories=_int_or_none(row.get("target_calories")),
                target_meters=_int_or_none(row.get("target_meters")),
            )
            results.append(record)
        except Exception:
            logger.warning(
                "Failed to parse DailyActivity for day=%s", day, exc_info=True
            )

    return results


def parse_daily_stress(path: Path) -> list[DailyStress]:
    """Parse daily stress data from dailystress.csv."""
    rows = _read_csv(path)
    results: list[DailyStress] = []

    for row in rows:
        day = row.get("day")
        if not day:
            continue

        try:
            record = DailyStress(
                day=day,
                day_summary=row.get("day_summary"),
                recovery_high=_int_or_none(row.get("recovery_high")),
                stress_high=_int_or_none(row.get("stress_high")),
            )
            results.append(record)
        except Exception:
            logger.warning(
                "Failed to parse DailyStress for day=%s", day, exc_info=True
            )

    return results


def parse_daily_spo2(path: Path) -> list[DailySpO2]:
    """Parse daily SpO2 data from dailyspo2.csv.

    Flattens spo2_percentage JSON to extract the average value.
    """
    rows = _read_csv(path)
    results: list[DailySpO2] = []

    for row in rows:
        day = row.get("day")
        if not day:
            continue

        # spo2_percentage is parsed as a dict by _read_csv (starts with '{')
        spo2_data = row.get("spo2_percentage")
        spo2_avg: Optional[float] = None
        if isinstance(spo2_data, dict):
            spo2_avg = _float_or_none(spo2_data.get("average"))

        try:
            record = DailySpO2(
                day=day,
                breathing_disturbance_index=_int_or_none(
                    row.get("breathing_disturbance_index")
                ),
                spo2_average=spo2_avg,
            )
            results.append(record)
        except Exception:
            logger.warning(
                "Failed to parse DailySpO2 for day=%s", day, exc_info=True
            )

    return results


def parse_daily_cardiovascular_age(path: Path) -> list[DailyCardiovascularAge]:
    """Parse daily cardiovascular age data from dailycardiovascularage.csv."""
    rows = _read_csv(path)
    results: list[DailyCardiovascularAge] = []

    for row in rows:
        day = row.get("day")
        if not day:
            continue

        try:
            record = DailyCardiovascularAge(
                day=day,
                vascular_age=_int_or_none(row.get("vascular_age")),
            )
            results.append(record)
        except Exception:
            logger.warning(
                "Failed to parse DailyCardiovascularAge for day=%s",
                day,
                exc_info=True,
            )

    return results


def parse_workouts(path: Path) -> list[Workout]:
    """Parse workout data from workout.csv."""
    rows = _read_csv(path)
    results: list[Workout] = []

    for row in rows:
        day = row.get("day")
        if not day:
            continue

        try:
            record = Workout(
                day=day,
                activity=row.get("activity"),
                calories=_float_or_none(row.get("calories")),
                distance=_float_or_none(row.get("distance")),
                start_datetime=_datetime_or_none(row.get("start_datetime")),
                end_datetime=_datetime_or_none(row.get("end_datetime")),
                intensity=row.get("intensity"),
                label=row.get("label"),
                source=row.get("source"),
            )
            results.append(record)
        except Exception:
            logger.warning(
                "Failed to parse Workout for day=%s", day, exc_info=True
            )

    return results


def parse_daily_resilience(path: Path) -> list[DailyResilience]:
    """Parse daily resilience data from dailyresilience.csv."""
    rows = _read_csv(path)
    results: list[DailyResilience] = []

    for row in rows:
        day = row.get("day")
        if not day:
            continue

        raw_contrib = row.get("contributors")
        contributors: Optional[ResilienceContributors] = None
        if isinstance(raw_contrib, dict):
            contributors = ResilienceContributors(
                daytime_recovery=_float_or_none(
                    raw_contrib.get("daytime_recovery")
                ),
                sleep_recovery=_float_or_none(raw_contrib.get("sleep_recovery")),
                stress=_float_or_none(raw_contrib.get("stress")),
            )

        try:
            record = DailyResilience(
                day=day,
                level=row.get("level"),
                contributors=contributors,
            )
            results.append(record)
        except Exception:
            logger.warning(
                "Failed to parse DailyResilience for day=%s", day, exc_info=True
            )

    return results


def parse_sleep_phases(sleepmodel_path: Path) -> list[SleepPhaseInterval]:
    """Parse sleep phase intervals from sleepmodel.csv.

    For each long_sleep row, parses the sleep_phase_5_min string where:
    - 1 = deep, 2 = light, 3 = rem, 4 = awake

    Each digit represents a 5-minute interval starting from bedtime_start.
    """
    rows = _read_csv(sleepmodel_path)
    results: list[SleepPhaseInterval] = []

    for row in rows:
        if row.get("type") != "long_sleep":
            continue

        day = row.get("day")
        if not day:
            continue

        phase_str = row.get("sleep_phase_5_min")
        if not phase_str or not isinstance(phase_str, str):
            continue

        bedtime_start = _datetime_or_none(row.get("bedtime_start"))
        if bedtime_start is None:
            logger.warning(
                "No bedtime_start for sleep phases on day=%s, skipping", day
            )
            continue

        for i, digit in enumerate(phase_str):
            phase = SLEEP_PHASE_MAP.get(digit)
            if phase is None:
                continue

            timestamp = bedtime_start + timedelta(minutes=5 * i)
            try:
                interval = SleepPhaseInterval(
                    day=day,
                    timestamp=timestamp,
                    phase=phase,
                    duration_seconds=300,
                )
                results.append(interval)
            except Exception:
                logger.warning(
                    "Failed to parse SleepPhaseInterval day=%s index=%d",
                    day,
                    i,
                    exc_info=True,
                )

    return results


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


@dataclass
class ParseResult:
    """Container for all parsed Oura export data."""

    sleep: list[DailySleep] = field(default_factory=list)
    readiness: list[DailyReadiness] = field(default_factory=list)
    activity: list[DailyActivity] = field(default_factory=list)
    stress: list[DailyStress] = field(default_factory=list)
    spo2: list[DailySpO2] = field(default_factory=list)
    cardiovascular_age: list[DailyCardiovascularAge] = field(default_factory=list)
    workouts: list[Workout] = field(default_factory=list)
    resilience: list[DailyResilience] = field(default_factory=list)
    sleep_phases: list[SleepPhaseInterval] = field(default_factory=list)


def parse_oura_export(export_dir: Path) -> ParseResult:
    """Parse all CSV files from an Oura data export directory.

    Args:
        export_dir: Path to the folder containing the exported CSV files.

    Returns:
        ParseResult with all parsed data types.

    Raises:
        FileNotFoundError: If any required CSV file is missing.
    """
    export_dir = Path(export_dir)

    # Required files — raise if missing
    required = {
        "dailysleep": export_dir / "dailysleep.csv",
        "sleepmodel": export_dir / "sleepmodel.csv",
        "dailyreadiness": export_dir / "dailyreadiness.csv",
        "dailyactivity": export_dir / "dailyactivity.csv",
    }

    for name, filepath in required.items():
        if not filepath.exists():
            raise FileNotFoundError(
                f"Required file '{name}.csv' not found in {export_dir}"
            )

    # Optional files — skip if missing
    optional = {
        "dailystress": export_dir / "dailystress.csv",
        "dailyspo2": export_dir / "dailyspo2.csv",
        "dailycardiovascularage": export_dir / "dailycardiovascularage.csv",
        "workout": export_dir / "workout.csv",
        "dailyresilience": export_dir / "dailyresilience.csv",
    }

    result = ParseResult()

    # Parse required files
    result.sleep = parse_daily_sleep(required["dailysleep"], required["sleepmodel"])
    result.readiness = parse_daily_readiness(required["dailyreadiness"])
    result.activity = parse_daily_activity(required["dailyactivity"])
    result.sleep_phases = parse_sleep_phases(required["sleepmodel"])

    # Parse optional files
    if optional["dailystress"].exists():
        result.stress = parse_daily_stress(optional["dailystress"])

    if optional["dailyspo2"].exists():
        result.spo2 = parse_daily_spo2(optional["dailyspo2"])

    if optional["dailycardiovascularage"].exists():
        result.cardiovascular_age = parse_daily_cardiovascular_age(
            optional["dailycardiovascularage"]
        )

    if optional["workout"].exists():
        result.workouts = parse_workouts(optional["workout"])

    if optional["dailyresilience"].exists():
        result.resilience = parse_daily_resilience(optional["dailyresilience"])

    total = (
        len(result.sleep)
        + len(result.readiness)
        + len(result.activity)
        + len(result.stress)
        + len(result.spo2)
        + len(result.cardiovascular_age)
        + len(result.workouts)
        + len(result.resilience)
        + len(result.sleep_phases)
    )
    logger.info("Oura export parsing complete: %d total records", total)

    return result
