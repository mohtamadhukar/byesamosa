"""Query and analytics functions for Oura Ring data."""

import json
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from byesamosa.data.models import Baseline
from byesamosa.data.store import DataStore


def compute_baselines(store: DataStore) -> list[Baseline]:
    """Compute rolling baselines for all tracked metrics.

    Returns a list of Baseline records (one per day per metric) with
    7-day, 30-day, and 90-day rolling averages and 30-day std deviation.
    """
    # Load all data
    sleep_records = store.load_sleep()
    readiness_records = store.load_readiness()
    activity_records = store.load_activity()

    if not sleep_records:
        return []

    # Convert to DataFrames
    sleep_df = pd.DataFrame([r.model_dump() for r in sleep_records])
    readiness_df = pd.DataFrame([r.model_dump() for r in readiness_records])
    activity_df = pd.DataFrame([r.model_dump() for r in activity_records])

    # Ensure 'day' is datetime
    sleep_df["day"] = pd.to_datetime(sleep_df["day"])
    readiness_df["day"] = pd.to_datetime(readiness_df["day"])
    activity_df["day"] = pd.to_datetime(activity_df["day"])

    # Sort by day
    sleep_df = sleep_df.sort_values("day")
    readiness_df = readiness_df.sort_values("day")
    activity_df = activity_df.sort_values("day")

    # Tracked metrics and their sources
    metrics_config = {
        "sleep_score": ("sleep", "score"),
        "readiness_score": ("readiness", "score"),
        "activity_score": ("activity", "score"),
        "average_hrv": ("sleep", "average_hrv"),
        "lowest_heart_rate": ("sleep", "lowest_heart_rate"),
        "deep_sleep_duration": ("sleep", "deep_sleep_duration"),
        "rem_sleep_duration": ("sleep", "rem_sleep_duration"),
        "total_sleep_duration": ("sleep", "total_sleep_duration"),
        "efficiency": ("sleep", "efficiency"),
        "temperature_deviation": ("readiness", "temperature_deviation"),
        "steps": ("activity", "steps"),
        "active_calories": ("activity", "active_calories"),
    }

    baselines = []

    for metric, (source, column) in metrics_config.items():
        if source == "sleep":
            df = sleep_df
        elif source == "readiness":
            df = readiness_df
        else:
            df = activity_df

        if column not in df.columns:
            continue

        # Compute rolling windows
        df_copy = df[["day", column]].copy()

        df_copy["avg_7d"] = df_copy[column].rolling(window=7, min_periods=1).mean()
        df_copy["avg_30d"] = df_copy[column].rolling(window=30, min_periods=1).mean()
        df_copy["avg_90d"] = df_copy[column].rolling(window=90, min_periods=1).mean()
        df_copy["std_30d"] = df_copy[column].rolling(window=30, min_periods=1).std()

        # Create Baseline records
        for _, row in df_copy.iterrows():
            baselines.append(
                Baseline(
                    schema_version=1,
                    day=row["day"].date(),
                    metric=metric,
                    avg_7d=round(row["avg_7d"], 2) if pd.notna(row["avg_7d"]) else None,
                    avg_30d=round(row["avg_30d"], 2)
                    if pd.notna(row["avg_30d"])
                    else None,
                    avg_90d=round(row["avg_90d"], 2)
                    if pd.notna(row["avg_90d"])
                    else None,
                    std_30d=round(row["std_30d"], 2)
                    if pd.notna(row["std_30d"])
                    else None,
                )
            )

    # Save to JSON
    baselines_file = store.processed_dir / "baselines.json"
    with open(baselines_file, "w") as f:
        json.dump([b.model_dump(mode="json") for b in baselines], f, indent=2)

    return baselines


def get_latest_day(store: DataStore) -> dict:
    """Get the latest day's data across all domains."""
    sleep_records = store.load_sleep()
    readiness_records = store.load_readiness()
    activity_records = store.load_activity()
    stress_records = store.load_stress()
    spo2_records = store.load_spo2()
    cardio_records = store.load_cardiovascular_age()

    if not sleep_records:
        return {}

    latest_sleep = max(sleep_records, key=lambda r: r.day)
    target_day = latest_sleep.day

    latest_readiness = max(readiness_records, key=lambda r: r.day) if readiness_records else None
    latest_activity = max(activity_records, key=lambda r: r.day) if activity_records else None

    # Find matching-day records for supplementary data types
    latest_stress = next((r for r in stress_records if r.day == target_day), None)
    latest_spo2 = next((r for r in spo2_records if r.day == target_day), None)
    latest_cardio = next((r for r in cardio_records if r.day == target_day), None)

    result = {
        "day": target_day,
        "sleep": latest_sleep.model_dump(),
        "readiness": latest_readiness.model_dump() if latest_readiness else None,
        "activity": latest_activity.model_dump() if latest_activity else None,
    }

    if latest_stress:
        result["stress"] = latest_stress.model_dump()
    if latest_spo2:
        result["spo2"] = latest_spo2.model_dump()
    if latest_cardio:
        result["cardiovascular_age"] = latest_cardio.model_dump()

    return result


def get_trends(store: DataStore, metric: str, days: int = 30) -> list[dict]:
    """Get time series data for a metric over the last N days.

    Returns list of {day, value} dicts suitable for sparklines/charts.
    """
    # Determine source
    metric_sources = {
        "sleep_score": ("sleep", "score"),
        "readiness_score": ("readiness", "score"),
        "activity_score": ("activity", "score"),
        "average_hrv": ("sleep", "average_hrv"),
        "lowest_heart_rate": ("sleep", "lowest_heart_rate"),
        "steps": ("activity", "steps"),
        "active_calories": ("activity", "active_calories"),
    }

    if metric not in metric_sources:
        return []

    source, column = metric_sources[metric]

    if source == "sleep":
        records = store.load_sleep()
    elif source == "readiness":
        records = store.load_readiness()
    else:
        records = store.load_activity()

    # Get latest N days
    sorted_records = sorted(records, key=lambda r: r.day, reverse=True)[:days]
    sorted_records = sorted(sorted_records, key=lambda r: r.day)

    return [
        {"day": r.day.isoformat(), "value": getattr(r, column)}
        for r in sorted_records
        if getattr(r, column) is not None
    ]


def get_deltas(store: DataStore, target_date: Optional[date] = None) -> dict:
    """Get delta values (today vs 30d avg) for each primary score.

    Returns dict with keys: sleep_delta, readiness_delta, activity_delta.
    """
    if target_date is None:
        latest = get_latest_day(store)
        if not latest:
            return {}
        target_date = latest["day"]

    # Load baselines
    baselines_file = store.processed_dir / "baselines.json"
    if not baselines_file.exists():
        return {}

    with open(baselines_file) as f:
        baselines_data = json.load(f)

    baselines = [Baseline.model_validate(b) for b in baselines_data]

    # Filter for target date
    date_baselines = [b for b in baselines if b.day == target_date]

    deltas = {}

    for metric in ["sleep_score", "readiness_score", "activity_score"]:
        baseline = next((b for b in date_baselines if b.metric == metric), None)
        if baseline and baseline.avg_30d is not None:
            # Get actual value for this day
            if metric == "sleep_score":
                records = store.load_sleep()
                record = next((r for r in records if r.day == target_date), None)
                if record and record.score is not None:
                    deltas["sleep_delta"] = record.score - baseline.avg_30d
            elif metric == "readiness_score":
                records = store.load_readiness()
                record = next((r for r in records if r.day == target_date), None)
                if record and record.score is not None:
                    deltas["readiness_delta"] = record.score - baseline.avg_30d
            else:
                records = store.load_activity()
                record = next((r for r in records if r.day == target_date), None)
                if record and record.score is not None:
                    deltas["activity_delta"] = record.score - baseline.avg_30d

    return deltas


def has_sleep_phases(store: DataStore) -> bool:
    """Check if sleep phase interval data is available."""
    phases = store.load_sleep_phases()
    return len(phases) > 0
