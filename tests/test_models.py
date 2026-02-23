"""Test data models and schema validation."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError
from byesamosa.data.models import DailyActivity, DailyReadiness, DailySleep


class TestDailySleep:
    """Tests for DailySleep model."""

    def test_create_minimal(self):
        """Test creating DailySleep with minimal fields."""
        sleep = DailySleep(day=date(2025, 1, 1))
        assert sleep.day == date(2025, 1, 1)
        assert sleep.sleep_score is None

    def test_create_full(self):
        """Test creating DailySleep with all fields."""
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
            bedtime_start=datetime(2025, 1, 1, 22, 0),
            bedtime_end=datetime(2025, 1, 2, 6, 0),
        )
        assert sleep.sleep_score == 85
        assert sleep.efficiency == 0.9

    def test_schema_version(self):
        """Test that schema_version is set."""
        sleep = DailySleep(day=date(2025, 1, 1))
        assert sleep.schema_version == 1

    def test_date_validation(self):
        """Test that day must be a valid date."""
        with pytest.raises(ValidationError):
            DailySleep(day="invalid")

    def test_optional_fields(self):
        """Test that optional fields work correctly."""
        sleep = DailySleep(
            day=date(2025, 1, 1),
            sleep_score=85,
            # Leave other fields as None
        )
        assert sleep.sleep_score == 85
        assert sleep.total_sleep_seconds is None

    def test_numeric_fields(self):
        """Test numeric field constraints."""
        sleep = DailySleep(
            day=date(2025, 1, 1),
            sleep_score=85,
            lowest_heart_rate=48,
        )
        assert isinstance(sleep.lowest_heart_rate, int)
        assert sleep.lowest_heart_rate == 48

    def test_json_serialization(self):
        """Test that model can be serialized to JSON."""
        sleep = DailySleep(
            day=date(2025, 1, 1),
            sleep_score=85,
            efficiency=0.9,
        )
        json_str = sleep.model_dump_json()
        assert "2025-01-01" in json_str
        assert "85" in json_str


class TestDailyReadiness:
    """Tests for DailyReadiness model."""

    def test_create_minimal(self):
        """Test creating DailyReadiness with minimal fields."""
        readiness = DailyReadiness(day=date(2025, 1, 1))
        assert readiness.day == date(2025, 1, 1)

    def test_create_full(self):
        """Test creating DailyReadiness with all fields."""
        readiness = DailyReadiness(
            day=date(2025, 1, 1),
            readiness_score=80,
            hrv_balance=0.85,
            recovery_index=0.8,
            temperature_trend=0.1,
            sleep_balance=0.75,
        )
        assert readiness.readiness_score == 80
        assert readiness.hrv_balance == 0.85

    def test_schema_version(self):
        """Test that schema_version is set."""
        readiness = DailyReadiness(day=date(2025, 1, 1))
        assert readiness.schema_version == 1

    def test_float_fields(self):
        """Test float field handling."""
        readiness = DailyReadiness(
            day=date(2025, 1, 1),
            hrv_balance=0.85,
            recovery_index=0.8,
        )
        assert isinstance(readiness.hrv_balance, float)
        assert readiness.hrv_balance == 0.85


class TestDailyActivity:
    """Tests for DailyActivity model."""

    def test_create_minimal(self):
        """Test creating DailyActivity with minimal fields."""
        activity = DailyActivity(day=date(2025, 1, 1))
        assert activity.day == date(2025, 1, 1)

    def test_create_full(self):
        """Test creating DailyActivity with all fields."""
        activity = DailyActivity(
            day=date(2025, 1, 1),
            activity_score=75,
            steps=8500,
            active_calories=450,
        )
        assert activity.activity_score == 75
        assert activity.steps == 8500

    def test_schema_version(self):
        """Test that schema_version is set."""
        activity = DailyActivity(day=date(2025, 1, 1))
        assert activity.schema_version == 1

    def test_steps_field(self):
        """Test steps field."""
        activity = DailyActivity(
            day=date(2025, 1, 1),
            steps=10000,
        )
        assert activity.steps == 10000


class TestModelInteroperability:
    """Test models working together."""

    def test_same_day_different_models(self):
        """Test that different models can represent same day."""
        test_date = date(2025, 1, 1)
        
        sleep = DailySleep(day=test_date, sleep_score=85)
        readiness = DailyReadiness(day=test_date, readiness_score=80)
        activity = DailyActivity(day=test_date, activity_score=75)
        
        assert sleep.day == readiness.day == activity.day

    def test_model_serialization_round_trip(self):
        """Test serialization and deserialization."""
        original = DailySleep(
            day=date(2025, 1, 1),
            sleep_score=85,
            efficiency=0.9,
        )
        
        json_data = original.model_dump_json()
        restored = DailySleep.model_validate_json(json_data)
        
        assert restored.day == original.day
        assert restored.sleep_score == original.sleep_score
        assert restored.efficiency == original.efficiency


class TestModelEdgeCases:
    """Test edge cases in models."""

    def test_zero_values(self):
        """Test that zero values are valid."""
        sleep = DailySleep(
            day=date(2025, 1, 1),
            sleep_score=0,
            lowest_heart_rate=0,
        )
        assert sleep.sleep_score == 0

    def test_large_values(self):
        """Test that large values are valid."""
        activity = DailyActivity(
            day=date(2025, 1, 1),
            steps=100000,
            active_calories=5000,
        )
        assert activity.steps == 100000

    def test_negative_temperature_deviation(self):
        """Test negative temperature deviation."""
        sleep = DailySleep(
            day=date(2025, 1, 1),
            temperature_deviation=-0.5,
        )
        assert sleep.temperature_deviation == -0.5

    def test_fractional_efficiency(self):
        """Test fractional efficiency values."""
        sleep = DailySleep(
            day=date(2025, 1, 1),
            efficiency=0.876543,
        )
        assert sleep.efficiency == 0.876543
