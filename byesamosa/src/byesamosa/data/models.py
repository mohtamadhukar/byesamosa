"""Pydantic models for Oura Ring data.

Updated to match real Oura CSV export structure (schema v2).
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Contributor sub-models
# ---------------------------------------------------------------------------


class SleepContributors(BaseModel):
    """Score contributors from dailysleep.csv."""

    deep_sleep: Optional[int] = None
    efficiency: Optional[int] = None
    latency: Optional[int] = None
    rem_sleep: Optional[int] = None
    restfulness: Optional[int] = None
    timing: Optional[int] = None
    total_sleep: Optional[int] = None


class ReadinessContributors(BaseModel):
    """Score contributors from dailyreadiness.csv."""

    activity_balance: Optional[int] = None
    body_temperature: Optional[int] = None
    hrv_balance: Optional[int] = None
    previous_day_activity: Optional[int] = None
    previous_night: Optional[int] = None
    recovery_index: Optional[int] = None
    resting_heart_rate: Optional[int] = None
    sleep_balance: Optional[int] = None
    sleep_regularity: Optional[int] = None


class ActivityContributors(BaseModel):
    """Score contributors from dailyactivity.csv."""

    meet_daily_targets: Optional[int] = None
    move_every_hour: Optional[int] = None
    recovery_time: Optional[int] = None
    stay_active: Optional[int] = None
    training_frequency: Optional[int] = None
    training_volume: Optional[int] = None


class ResilienceContributors(BaseModel):
    """Score contributors from dailyresilience.csv."""

    daytime_recovery: Optional[float] = None
    sleep_recovery: Optional[float] = None
    stress: Optional[float] = None


# ---------------------------------------------------------------------------
# Core daily models
# ---------------------------------------------------------------------------


class DailySleep(BaseModel):
    """Nightly sleep summary — merged from dailysleep.csv + sleepmodel.csv."""

    schema_version: int = 2
    day: date
    score: Optional[int] = None
    contributors: Optional[SleepContributors] = None

    # Raw metrics from sleepmodel.csv
    total_sleep_duration: Optional[int] = None
    rem_sleep_duration: Optional[int] = None
    deep_sleep_duration: Optional[int] = None
    light_sleep_duration: Optional[int] = None
    awake_time: Optional[int] = None
    time_in_bed: Optional[int] = None
    efficiency: Optional[int] = None
    average_hrv: Optional[int] = None
    average_heart_rate: Optional[int] = None
    average_breath: Optional[float] = None
    lowest_heart_rate: Optional[int] = None
    restless_periods: Optional[int] = None
    temperature_deviation: Optional[float] = None
    bedtime_start: Optional[datetime] = None
    bedtime_end: Optional[datetime] = None


class DailyReadiness(BaseModel):
    """Daily readiness/recovery metrics from dailyreadiness.csv."""

    schema_version: int = 2
    day: date
    score: Optional[int] = None
    contributors: Optional[ReadinessContributors] = None
    temperature_deviation: Optional[float] = None
    temperature_trend_deviation: Optional[float] = None


class DailyActivity(BaseModel):
    """Daily activity metrics from dailyactivity.csv."""

    schema_version: int = 2
    day: date
    score: Optional[int] = None
    contributors: Optional[ActivityContributors] = None
    steps: Optional[int] = None
    active_calories: Optional[int] = None
    total_calories: Optional[int] = None
    high_activity_time: Optional[int] = None
    medium_activity_time: Optional[int] = None
    low_activity_time: Optional[int] = None
    sedentary_time: Optional[int] = None
    resting_time: Optional[int] = None
    non_wear_time: Optional[int] = None
    equivalent_walking_distance: Optional[int] = None
    inactivity_alerts: Optional[int] = None
    target_calories: Optional[int] = None
    target_meters: Optional[int] = None


# ---------------------------------------------------------------------------
# New data types
# ---------------------------------------------------------------------------


class DailyStress(BaseModel):
    """Daily stress summary from dailystress.csv."""

    schema_version: int = 1
    day: date
    day_summary: Optional[str] = None
    recovery_high: Optional[int] = None
    stress_high: Optional[int] = None


class DailySpO2(BaseModel):
    """Daily SpO2 from dailyspo2.csv (spo2_percentage JSON flattened)."""

    schema_version: int = 1
    day: date
    breathing_disturbance_index: Optional[int] = None
    spo2_average: Optional[float] = None


class DailyCardiovascularAge(BaseModel):
    """Daily cardiovascular age from dailycardiovascularage.csv."""

    schema_version: int = 1
    day: date
    vascular_age: Optional[int] = None


class Workout(BaseModel):
    """Workout record from workout.csv."""

    schema_version: int = 1
    day: date
    activity: Optional[str] = None
    calories: Optional[float] = None
    distance: Optional[float] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    intensity: Optional[str] = None
    label: Optional[str] = None
    source: Optional[str] = None


class DailyResilience(BaseModel):
    """Daily resilience from dailyresilience.csv."""

    schema_version: int = 1
    day: date
    level: Optional[str] = None
    contributors: Optional[ResilienceContributors] = None


# ---------------------------------------------------------------------------
# Unchanged models
# ---------------------------------------------------------------------------


class SleepPhaseInterval(BaseModel):
    """5-minute resolution sleep phase data for hypnogram visualization.

    Note: This data may not be available in all Oura exports. The parser
    and API will handle cases where interval-level data is missing.
    """

    schema_version: int = 1
    day: date
    timestamp: datetime
    phase: Literal["awake", "rem", "light", "deep"]
    duration_seconds: int = 300


class Baseline(BaseModel):
    """Rolling baseline statistics for a metric."""

    schema_version: int = 1
    day: date
    metric: str
    avg_7d: Optional[float] = None
    avg_30d: Optional[float] = None
    avg_90d: Optional[float] = None
    std_30d: Optional[float] = None
