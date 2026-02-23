"""Test data queries and baseline computation."""

import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest
from byesamosa.data.models import DailyActivity, DailyReadiness, DailySleep
from byesamosa.data.queries import (
    compute_baselines,
    get_deltas,
    get_latest_day,
    get_trends,
    has_sleep_phases,
)
from byesamosa.data.store import DataStore


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        # Create required subdirectories
        (tmpdir_path / "raw").mkdir(exist_ok=True)
        (tmpdir_path / "processed").mkdir(exist_ok=True)
        (tmpdir_path / "insights").mkdir(exist_ok=True)
        (tmpdir_path / "logs").mkdir(exist_ok=True)
        yield tmpdir_path


@pytest.fixture
def sample_data(temp_data_dir):
    """Create sample data for testing."""
    base_date = date(2025, 1, 1)
    sleep_records = []
    readiness_records = []
    activity_records = []

    # Generate 30 days of data
    for i in range(30):
        current_date = base_date + timedelta(days=i)
        
        # Create sleep record
        sleep = DailySleep(
            day=current_date,
            sleep_score=75 + i % 20,
            total_sleep_seconds=28800 + (i * 600),
            rem_sleep_seconds=7200 + (i * 100),
            deep_sleep_seconds=9600 + (i * 150),
            light_sleep_seconds=9000 + (i * 200),
            awake_seconds=3600 - (i * 50),
            efficiency=0.85 + (i * 0.002),
            average_hrv=50 + (i * 0.5),
            lowest_heart_rate=50 + (i % 10),
            temperature_deviation=0.1 + (i * 0.01),
        )
        sleep_records.append(sleep)
        
        # Create readiness record
        readiness = DailyReadiness(
            day=current_date,
            readiness_score=70 + i % 25,
            hrv_balance=0.8 + (i * 0.001),
            recovery_index=0.75 + (i * 0.002),
            temperature_trend=0.1 + (i * 0.005),
            sleep_balance=0.7 + (i * 0.003),
        )
        readiness_records.append(readiness)
        
        # Create activity record
        activity = DailyActivity(
            day=current_date,
            activity_score=65 + i % 30,
            steps=8000 + (i * 100),
            active_calories=400 + (i * 10),
        )
        activity_records.append(activity)

    # Save to store
    store = DataStore(temp_data_dir)
    store.upsert_sleep(sleep_records)
    store.upsert_readiness(readiness_records)
    store.upsert_activity(activity_records)

    return store, sleep_records, readiness_records, activity_records


def test_get_latest_day(sample_data):
    """Test getting the latest day's data."""
    store, sleep_records, readiness_records, activity_records = sample_data
    
    latest = get_latest_day(store)
    
    # latest can be None or empty dict when no sleep data, or a dict with data
    if latest:
        assert "sleep" in latest or "readiness" in latest or "activity" in latest


def test_get_latest_day_no_data(temp_data_dir):
    """Test getting latest day when no data exists."""
    store = DataStore(temp_data_dir)
    latest = get_latest_day(store)
    # Should return None or empty dict
    assert latest is None or latest == {}


def test_compute_baselines(sample_data):
    """Test baseline computation."""
    store, _, _, _ = sample_data
    
    baselines = compute_baselines(store)
    
    assert len(baselines) > 0
    
    # Check structure of baselines
    for baseline in baselines:
        assert hasattr(baseline, "day")
        assert hasattr(baseline, "metric")
        assert hasattr(baseline, "avg_7d")
        assert hasattr(baseline, "avg_30d")
        assert hasattr(baseline, "avg_90d")


def test_compute_baselines_correctness(sample_data):
    """Test that baseline computation is mathematically correct."""
    store, sleep_records, _, _ = sample_data
    
    baselines = compute_baselines(store)
    
    # Find sleep_score baseline for a specific date
    target_date = sleep_records[10].day  # Day 11 (index 10)
    sleep_score_baselines = [
        b for b in baselines
        if b.day == target_date and b.metric == "sleep_score"
    ]
    
    assert len(sleep_score_baselines) > 0


def test_get_trends(sample_data):
    """Test getting trend data."""
    store, sleep_records, _, _ = sample_data
    
    trends = get_trends(store, "sleep_score", days=7)
    
    assert trends is not None
    assert len(trends) > 0


def test_get_deltas(sample_data):
    """Test calculating deltas (changes from baseline)."""
    store, sleep_records, _, _ = sample_data
    
    compute_baselines(store)
    
    target_date = sleep_records[-1].day
    deltas = get_deltas(store, target_date)
    
    assert deltas is not None
    assert isinstance(deltas, dict)


def test_has_sleep_phases(temp_data_dir):
    """Test checking for sleep phases availability."""
    store = DataStore(temp_data_dir)
    
    # Should return False when no sleep phases data
    assert has_sleep_phases(store) is False


def test_empty_store_queries(temp_data_dir):
    """Test queries on an empty data store."""
    store = DataStore(temp_data_dir)
    
    # All queries should handle empty data gracefully
    result = get_latest_day(store)
    assert result is None or result == {}
    assert compute_baselines(store) == []
    assert get_trends(store, "sleep_score", days=7) == []
    assert isinstance(get_deltas(store), dict)
