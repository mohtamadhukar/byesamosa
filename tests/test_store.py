"""Test data store functionality."""

import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest
from byesamosa.data.models import DailyActivity, DailyReadiness, DailySleep
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
def store(temp_data_dir):
    """Create a DataStore instance."""
    return DataStore(temp_data_dir)


def test_store_initialization(temp_data_dir):
    """Test DataStore initialization."""
    store = DataStore(temp_data_dir)
    assert store.data_dir == temp_data_dir


def test_upsert_sleep(store):
    """Test upserting sleep records."""
    sleep = DailySleep(
        day=date(2025, 1, 1),
        sleep_score=85,
        total_sleep_seconds=28800,
        rem_sleep_seconds=7200,
        deep_sleep_seconds=9600,
        light_sleep_seconds=9000,
        awake_seconds=3600,
        efficiency=0.9,
        average_hrv=55,
        lowest_heart_rate=48,
        temperature_deviation=0.05,
    )
    
    store.upsert_sleep([sleep])
    
    # Verify file was created
    sleep_file = store.data_dir / "processed" / "daily_sleep.json"
    assert sleep_file.exists()


def test_upsert_readiness(store):
    """Test upserting readiness records."""
    readiness = DailyReadiness(
        day=date(2025, 1, 1),
        readiness_score=80,
        hrv_balance=0.85,
        recovery_index=0.8,
        temperature_trend=0.1,
        sleep_balance=0.75,
    )
    
    store.upsert_readiness([readiness])
    
    readiness_file = store.data_dir / "processed" / "daily_readiness.json"
    assert readiness_file.exists()


def test_upsert_activity(store):
    """Test upserting activity records."""
    activity = DailyActivity(
        day=date(2025, 1, 1),
        activity_score=75,
        steps=8500,
        active_calories=450,
    )
    
    store.upsert_activity([activity])
    
    activity_file = store.data_dir / "processed" / "daily_activity.json"
    assert activity_file.exists()


def test_load_sleep(store):
    """Test loading sleep records."""
    sleep = DailySleep(
        day=date(2025, 1, 1),
        sleep_score=85,
        total_sleep_seconds=28800,
    )
    
    store.upsert_sleep([sleep])
    records = store.load_sleep()
    
    assert len(records) > 0
    assert records[0].day == date(2025, 1, 1)
    assert records[0].sleep_score == 85


def test_load_readiness(store):
    """Test loading readiness records."""
    readiness = DailyReadiness(
        day=date(2025, 1, 1),
        readiness_score=80,
    )
    
    store.upsert_readiness([readiness])
    records = store.load_readiness()
    
    assert len(records) > 0
    assert records[0].day == date(2025, 1, 1)
    assert records[0].readiness_score == 80


def test_load_activity(store):
    """Test loading activity records."""
    activity = DailyActivity(
        day=date(2025, 1, 1),
        activity_score=75,
        steps=8500,
    )
    
    store.upsert_activity([activity])
    records = store.load_activity()
    
    assert len(records) > 0
    assert records[0].day == date(2025, 1, 1)
    assert records[0].activity_score == 75


def test_deduplication(store):
    """Test that upserting same day twice only keeps one record."""
    sleep1 = DailySleep(
        day=date(2025, 1, 1),
        sleep_score=85,
    )
    sleep2 = DailySleep(
        day=date(2025, 1, 1),
        sleep_score=90,  # Different value
    )
    
    store.upsert_sleep([sleep1])
    store.upsert_sleep([sleep2])
    
    records = store.load_sleep()
    
    # Should only have one record for 2025-01-01
    jan1_records = [r for r in records if r.day == date(2025, 1, 1)]
    assert len(jan1_records) == 1
    # Should have the latest value
    assert jan1_records[0].sleep_score == 90


def test_multiple_records(store):
    """Test storing and loading multiple records."""
    sleep_records = []
    for i in range(5):
        sleep = DailySleep(
            day=date(2025, 1, i + 1),
            sleep_score=80 + i,
        )
        sleep_records.append(sleep)
    
    store.upsert_sleep(sleep_records)
    
    records = store.load_sleep()
    assert len(records) == 5
    
    # Verify records are in chronological order
    for i, record in enumerate(records):
        assert record.day == date(2025, 1, i + 1)


def test_load_nonexistent_file(store):
    """Test loading when file doesn't exist yet."""
    records = store.load_sleep()
    assert records == []


def test_round_trip(store):
    """Test round-trip: create → upsert → load → verify."""
    original = DailySleep(
        day=date(2025, 1, 1),
        sleep_score=85,
        total_sleep_seconds=28800,
        rem_sleep_seconds=7200,
        deep_sleep_seconds=9600,
        efficiency=0.9,
        average_hrv=55,
        lowest_heart_rate=48,
    )
    
    store.upsert_sleep([original])
    records = store.load_sleep()
    loaded = records[0]
    
    assert loaded.day == original.day
    assert loaded.sleep_score == original.sleep_score
    assert loaded.total_sleep_seconds == original.total_sleep_seconds
    assert loaded.efficiency == original.efficiency
