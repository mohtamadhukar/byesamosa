"""Generate mock JSON data directly for API development."""

import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)

DATA_DIR = Path("data")
PROCESSED_DIR = DATA_DIR / "processed"
INSIGHTS_DIR = DATA_DIR / "insights"
DAYS = 30
END_DATE = date.today()
START_DATE = END_DATE - timedelta(days=DAYS - 1)


def generate_all_data():
    """Generate complete mock dataset as JSON."""
    
    sleep_records = []
    readiness_records = []
    activity_records = []
    sleep_phases = []
    
    for i in range(DAYS):
        day = START_DATE + timedelta(days=i)
        
        # Sleep data
        total_sleep_hours = random.uniform(6.5, 9.0)
        total_sleep_seconds = int(total_sleep_hours * 3600)
        efficiency = random.uniform(0.85, 0.96)
        
        sleep_score = int(70 + (total_sleep_hours - 6.5) * 5 + efficiency * 10 + random.uniform(-5, 5))
        sleep_score = max(60, min(95, sleep_score))
        
        bedtime_start = datetime.combine(day - timedelta(days=1), datetime.min.time()).replace(
            hour=random.randint(22, 23), minute=random.randint(0, 59)
        )
        bedtime_end = bedtime_start + timedelta(seconds=total_sleep_seconds)
        
        sleep_records.append({
            "schema_version": 1,
            "day": day.isoformat(),
            "sleep_score": sleep_score,
            "total_sleep_seconds": total_sleep_seconds,
            "rem_sleep_seconds": int(total_sleep_seconds * random.uniform(0.20, 0.25)),
            "deep_sleep_seconds": int(total_sleep_seconds * random.uniform(0.15, 0.20)),
            "light_sleep_seconds": int(total_sleep_seconds * random.uniform(0.50, 0.60)),
            "awake_seconds": int(total_sleep_seconds * random.uniform(0.05, 0.10)),
            "efficiency": round(efficiency, 3),
            "average_hrv": round(random.uniform(30, 80), 1),
            "lowest_heart_rate": random.randint(45, 65),
            "temperature_deviation": round(random.uniform(-0.5, 0.5), 2),
            "bedtime_start": bedtime_start.isoformat(),
            "bedtime_end": bedtime_end.isoformat(),
        })
        
        # Readiness data (correlated with sleep)
        readiness_score = int(sleep_score + random.uniform(-10, 10))
        readiness_score = max(60, min(95, readiness_score))
        
        readiness_records.append({
            "schema_version": 1,
            "day": day.isoformat(),
            "readiness_score": readiness_score,
            "hrv_balance": round(random.uniform(0.7, 1.3), 2),
            "recovery_index": round(random.uniform(0.6, 1.0), 2),
            "temperature_trend": round(random.uniform(-0.3, 0.3), 2),
            "sleep_balance": round(random.uniform(0.8, 1.2), 2),
        })
        
        # Activity data
        steps = random.randint(5000, 15000)
        active_calories = random.randint(300, 800)
        activity_score = int(60 + (steps / 10000) * 20 + random.uniform(-5, 5))
        activity_score = max(60, min(95, activity_score))
        
        activity_records.append({
            "schema_version": 1,
            "day": day.isoformat(),
            "activity_score": activity_score,
            "steps": steps,
            "active_calories": active_calories,
            "total_calories": active_calories + random.randint(1200, 1800),
            "inactive_time_seconds": random.randint(28800, 43200),
            "low_activity_time_seconds": random.randint(7200, 14400),
            "medium_activity_time_seconds": random.randint(3600, 7200),
            "high_activity_time_seconds": random.randint(1800, 5400),
        })
    
    # Generate sleep phases for latest night only
    latest = sleep_records[-1]
    day = date.fromisoformat(latest["day"])
    bedtime_start = datetime.fromisoformat(latest["bedtime_start"])
    bedtime_end = datetime.fromisoformat(latest["bedtime_end"])
    
    current = bedtime_start
    while current < bedtime_end:
        # Simplified phase pattern
        elapsed = (current - bedtime_start).total_seconds()
        progress = elapsed / (bedtime_end - bedtime_start).total_seconds()
        
        if progress < 0.3:
            phase = random.choice(["deep", "light", "light"])
        elif progress < 0.7:
            phase = random.choice(["light", "rem"])
        else:
            phase = random.choice(["rem", "light"])
        
        if random.random() < 0.05:
            phase = "awake"
        
        sleep_phases.append({
            "schema_version": 1,
            "day": day.isoformat(),
            "timestamp": current.isoformat(),
            "phase": phase,
            "duration_seconds": 300,
        })
        
        current += timedelta(minutes=5)
    
    # Generate sample insight
    insight = {
        "date": END_DATE.isoformat(),
        "score_insights": {
            "sleep": {
                "one_liner": "Strong night with 7.5h total sleep and high efficiency",
                "contributors": [
                    {"name": "Total Sleep", "value": 87, "baseline": 82, "tag": "boost"},
                    {"name": "Efficiency", "value": 92, "baseline": 88, "tag": "boost"},
                    {"name": "Deep Sleep", "value": 75, "baseline": 78, "tag": "ok"},
                    {"name": "REM Sleep", "value": 78, "baseline": 75, "tag": "boost"},
                ],
                "good_looks_like": "All contributors ≥80, total sleep ≥7.5h, efficiency ≥90%",
            },
            "readiness": {
                "one_liner": "Body recovered well from yesterday's activity",
                "contributors": [
                    {"name": "HRV Balance", "value": 85, "baseline": 80, "tag": "boost"},
                    {"name": "Recovery Index", "value": 82, "baseline": 79, "tag": "ok"},
                ],
                "good_looks_like": "HRV balance >80, recovery index >0.85",
            },
            "activity": {
                "one_liner": "Good movement with 10K+ steps",
                "contributors": [
                    {"name": "Steps", "value": 78, "baseline": 72, "tag": "ok"},
                    {"name": "Active Calories", "value": 75, "baseline": 70, "tag": "ok"},
                ],
                "good_looks_like": "10K+ steps, 500+ active calories",
            },
        },
        "reasoning_chain": [
            {
                "observation": "Sleep efficiency at 92% with 7.5h total",
                "cause": "Consistent bedtime routine minimized disruptions",
                "implication": "Body completed full sleep cycles",
            },
            {
                "observation": "HRV elevated to 62ms vs 55ms baseline",
                "cause": "Parasympathetic nervous system in recovery mode",
                "implication": "Body adapted well to training load",
            },
        ],
        "actions": [
            {
                "text": "Maintain current bedtime window (10:30-11pm)",
                "priority": "high",
                "category": "sleep",
            },
            {
                "text": "Consider 15min morning sunlight exposure",
                "priority": "medium",
                "category": "sleep",
            },
        ],
        "hypnogram_annotation": {
            "text": "Strong REM rebound in final cycle — sign of good recovery",
        },
        "vital_annotations": {
            "hrv": {"text": "62ms is above your 30d average (55ms)"},
            "rhr": {"text": "52 bpm at lowest — slightly elevated vs baseline"},
        },
        "trend_annotations": {
            "sleep_score_30d": {
                "text": "Upward trend last 7 days",
                "icon": "trending_up",
            },
        },
    }
    
    return sleep_records, readiness_records, activity_records, sleep_phases, insight


def main():
    print("Generating mock JSON data...")
    
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    
    sleep, readiness, activity, phases, insight = generate_all_data()
    
    (PROCESSED_DIR / "daily_sleep.json").write_text(json.dumps(sleep, indent=2))
    print(f"✓ Created {len(sleep)} sleep records")
    
    (PROCESSED_DIR / "daily_readiness.json").write_text(json.dumps(readiness, indent=2))
    print(f"✓ Created {len(readiness)} readiness records")
    
    (PROCESSED_DIR / "daily_activity.json").write_text(json.dumps(activity, indent=2))
    print(f"✓ Created {len(activity)} activity records")
    
    (PROCESSED_DIR / "sleep_phases.json").write_text(json.dumps(phases, indent=2))
    print(f"✓ Created {len(phases)} sleep phase intervals")
    
    (INSIGHTS_DIR / f"{END_DATE.isoformat()}.json").write_text(json.dumps(insight, indent=2))
    print(f"✓ Created sample insight for {END_DATE}")
    
    print("\n✅ Mock JSON data generation complete!")


if __name__ == "__main__":
    main()
