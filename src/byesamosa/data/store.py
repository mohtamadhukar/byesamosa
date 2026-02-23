"""JSON data store for reading and writing processed Oura data."""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from byesamosa.data.models import (
    DailyActivity,
    DailyCardiovascularAge,
    DailyReadiness,
    DailyResilience,
    DailySleep,
    DailySpO2,
    DailyStress,
    SleepPhaseInterval,
    Workout,
)


class DataStore:
    """Handles loading and saving processed Oura Ring data from JSON files."""

    def __init__(self, data_dir: Path):
        """Initialize data store with base data directory."""
        self.data_dir = Path(data_dir)
        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def load_sleep(self) -> list[DailySleep]:
        """Load all sleep records from JSON."""
        file_path = self.processed_dir / "daily_sleep.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
        return [DailySleep.model_validate(record) for record in data]

    def load_readiness(self) -> list[DailyReadiness]:
        """Load all readiness records from JSON."""
        file_path = self.processed_dir / "daily_readiness.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
        return [DailyReadiness.model_validate(record) for record in data]

    def load_activity(self) -> list[DailyActivity]:
        """Load all activity records from JSON."""
        file_path = self.processed_dir / "daily_activity.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
        return [DailyActivity.model_validate(record) for record in data]

    def load_sleep_phases(self, day: Optional[date] = None) -> list[SleepPhaseInterval]:
        """Load sleep phase intervals, optionally filtered by day."""
        file_path = self.processed_dir / "sleep_phases.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)

        records = [SleepPhaseInterval.model_validate(record) for record in data]

        if day is not None:
            records = [r for r in records if r.day == day]

        return records

    def save_sleep(self, records: list[DailySleep]) -> None:
        """Write sleep records to JSON, sorted by day."""
        sorted_records = sorted(records, key=lambda r: r.day)
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "daily_sleep.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_readiness(self, records: list[DailyReadiness]) -> None:
        """Write readiness records to JSON, sorted by day."""
        sorted_records = sorted(records, key=lambda r: r.day)
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "daily_readiness.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_activity(self, records: list[DailyActivity]) -> None:
        """Write activity records to JSON, sorted by day."""
        sorted_records = sorted(records, key=lambda r: r.day)
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "daily_activity.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_sleep_phases(self, records: list[SleepPhaseInterval]) -> None:
        """Write sleep phase records to JSON, sorted by timestamp."""
        sorted_records = sorted(records, key=lambda r: (r.day, r.timestamp))
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "sleep_phases.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def upsert_sleep(self, new_records: list[DailySleep]) -> None:
        """Merge new sleep records with existing, deduplicating by day (new wins)."""
        existing = self.load_sleep()
        existing_map = {r.day: r for r in existing}

        # New records override existing for same day
        for record in new_records:
            existing_map[record.day] = record

        self.save_sleep(list(existing_map.values()))

    def upsert_readiness(self, new_records: list[DailyReadiness]) -> None:
        """Merge new readiness records with existing, deduplicating by day (new wins)."""
        existing = self.load_readiness()
        existing_map = {r.day: r for r in existing}

        for record in new_records:
            existing_map[record.day] = record

        self.save_readiness(list(existing_map.values()))

    def upsert_activity(self, new_records: list[DailyActivity]) -> None:
        """Merge new activity records with existing, deduplicating by day (new wins)."""
        existing = self.load_activity()
        existing_map = {r.day: r for r in existing}

        for record in new_records:
            existing_map[record.day] = record

        self.save_activity(list(existing_map.values()))

    def upsert_sleep_phases(self, new_records: list[SleepPhaseInterval]) -> None:
        """Merge new sleep phase records, deduplicating by (day, timestamp)."""
        existing = self.load_sleep_phases()
        existing_map = {(r.day, r.timestamp): r for r in existing}

        for record in new_records:
            existing_map[(record.day, record.timestamp)] = record

        self.save_sleep_phases(list(existing_map.values()))

    # ------------------------------------------------------------------
    # Stress
    # ------------------------------------------------------------------

    def load_stress(self) -> list[DailyStress]:
        """Load all stress records from JSON."""
        file_path = self.processed_dir / "daily_stress.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
        return [DailyStress.model_validate(record) for record in data]

    def save_stress(self, records: list[DailyStress]) -> None:
        """Write stress records to JSON, sorted by day."""
        sorted_records = sorted(records, key=lambda r: r.day)
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "daily_stress.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def upsert_stress(self, new_records: list[DailyStress]) -> None:
        """Merge new stress records with existing, deduplicating by day."""
        existing = self.load_stress()
        existing_map = {r.day: r for r in existing}

        for record in new_records:
            existing_map[record.day] = record

        self.save_stress(list(existing_map.values()))

    # ------------------------------------------------------------------
    # SpO2
    # ------------------------------------------------------------------

    def load_spo2(self) -> list[DailySpO2]:
        """Load all SpO2 records from JSON."""
        file_path = self.processed_dir / "daily_spo2.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
        return [DailySpO2.model_validate(record) for record in data]

    def save_spo2(self, records: list[DailySpO2]) -> None:
        """Write SpO2 records to JSON, sorted by day."""
        sorted_records = sorted(records, key=lambda r: r.day)
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "daily_spo2.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def upsert_spo2(self, new_records: list[DailySpO2]) -> None:
        """Merge new SpO2 records with existing, deduplicating by day."""
        existing = self.load_spo2()
        existing_map = {r.day: r for r in existing}

        for record in new_records:
            existing_map[record.day] = record

        self.save_spo2(list(existing_map.values()))

    # ------------------------------------------------------------------
    # Cardiovascular Age
    # ------------------------------------------------------------------

    def load_cardiovascular_age(self) -> list[DailyCardiovascularAge]:
        """Load all cardiovascular age records from JSON."""
        file_path = self.processed_dir / "daily_cardiovascular_age.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
        return [DailyCardiovascularAge.model_validate(record) for record in data]

    def save_cardiovascular_age(self, records: list[DailyCardiovascularAge]) -> None:
        """Write cardiovascular age records to JSON, sorted by day."""
        sorted_records = sorted(records, key=lambda r: r.day)
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "daily_cardiovascular_age.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def upsert_cardiovascular_age(self, new_records: list[DailyCardiovascularAge]) -> None:
        """Merge new cardiovascular age records with existing, deduplicating by day."""
        existing = self.load_cardiovascular_age()
        existing_map = {r.day: r for r in existing}

        for record in new_records:
            existing_map[record.day] = record

        self.save_cardiovascular_age(list(existing_map.values()))

    # ------------------------------------------------------------------
    # Workouts
    # ------------------------------------------------------------------

    def load_workouts(self) -> list[Workout]:
        """Load all workout records from JSON."""
        file_path = self.processed_dir / "workouts.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
        return [Workout.model_validate(record) for record in data]

    def save_workouts(self, records: list[Workout]) -> None:
        """Write workout records to JSON, sorted by day and start time."""
        sorted_records = sorted(records, key=lambda r: (r.day, r.start_datetime or datetime.min))
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "workouts.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def upsert_workouts(self, new_records: list[Workout]) -> None:
        """Merge new workout records with existing, deduplicating by (day, start_datetime)."""
        existing = self.load_workouts()
        existing_map = {(r.day, r.start_datetime): r for r in existing}

        for record in new_records:
            existing_map[(record.day, record.start_datetime)] = record

        self.save_workouts(list(existing_map.values()))

    # ------------------------------------------------------------------
    # Resilience
    # ------------------------------------------------------------------

    def load_resilience(self) -> list[DailyResilience]:
        """Load all resilience records from JSON."""
        file_path = self.processed_dir / "daily_resilience.json"
        if not file_path.exists():
            return []

        with open(file_path) as f:
            data = json.load(f)
        return [DailyResilience.model_validate(record) for record in data]

    def save_resilience(self, records: list[DailyResilience]) -> None:
        """Write resilience records to JSON, sorted by day."""
        sorted_records = sorted(records, key=lambda r: r.day)
        data = [r.model_dump(mode="json") for r in sorted_records]

        file_path = self.processed_dir / "daily_resilience.json"
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def upsert_resilience(self, new_records: list[DailyResilience]) -> None:
        """Merge new resilience records with existing, deduplicating by day."""
        existing = self.load_resilience()
        existing_map = {r.day: r for r in existing}

        for record in new_records:
            existing_map[record.day] = record

        self.save_resilience(list(existing_map.values()))
