#!/usr/bin/env python3
"""
Generate mock Oura Ring CSV export data for development.

Creates 30 days of realistic, correlated data across 4 CSV files:
- daily_sleep.csv
- daily_readiness.csv
- daily_activity.csv
- sleep.csv

Usage:
    python scripts/generate_mock_data.py [--days 30] [--start-date 2025-01-01] [--seed 42]
"""

import argparse
import csv
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

import numpy as np


# === PERSONA CONSTANTS ===
PERSONA = {
    "baseline_hrv": 50,  # ms
    "baseline_rhr": 56,  # bpm
    "baseline_temp": 0.0,  # deviation from user baseline
    "baseline_bedtime_hour": 23.0,  # 11 PM
    "baseline_waketime_hour": 7.0,  # 7 AM
    "baseline_steps": 8000,
    "baseline_calories": 2200,
}

# === STORY EVENTS ===
STORY_EVENTS = {
    15: {"type": "bad_night", "bedtime_delay": 2.0, "sleep_quality_penalty": -0.3},
    16: {"type": "sluggish_day", "activity_penalty": -0.2, "recovery_penalty": -0.1},
    17: {"type": "recovery_day", "activity_bonus": -0.3, "recovery_bonus": 0.2},
    10: {"type": "great_workout", "activity_bonus": 0.3, "next_day_recovery_penalty": -0.15},
    24: {"type": "peak_performance", "activity_bonus": 0.25, "recovery_bonus": 0.1},
}


def generate_latent_states(days: int, seed: int) -> Dict[str, np.ndarray]:
    """
    Generate latent person state across days.

    Returns dict with:
    - recovery: [0, 1], affects readiness/HRV/RHR/temp
    - sleep_quality: [0, 1], affects sleep score and next-day readiness
    - activity_drive: [0, 1], affects activity score and next-day recovery
    """
    np.random.seed(seed)

    recovery = np.zeros(days)
    sleep_quality = np.zeros(days)
    activity_drive = np.zeros(days)

    # Initialize at baseline
    recovery[0] = 0.7
    sleep_quality[0] = 0.75
    activity_drive[0] = 0.65

    for day in range(1, days):
        # Autoregressive evolution with mean reversion
        recovery[day] = 0.6 * recovery[day-1] + 0.3 * 0.7 + np.random.normal(0, 0.08)
        sleep_quality[day] = 0.5 * sleep_quality[day-1] + 0.4 * 0.75 + np.random.normal(0, 0.1)
        activity_drive[day] = 0.4 * activity_drive[day-1] + 0.5 * 0.65 + np.random.normal(0, 0.12)

        # Weekend effect (Sat=5, Sun=6)
        weekday = day % 7
        if weekday in [5, 6]:
            activity_drive[day] += 0.1
            sleep_quality[day] -= 0.05  # later bedtime

        # Story events
        if day in STORY_EVENTS:
            event = STORY_EVENTS[day]
            if "sleep_quality_penalty" in event:
                sleep_quality[day] += event["sleep_quality_penalty"]
            if "activity_penalty" in event:
                activity_drive[day] += event["activity_penalty"]
            if "activity_bonus" in event:
                activity_drive[day] += event["activity_bonus"]
            if "recovery_penalty" in event:
                recovery[day] += event["recovery_penalty"]
            if "recovery_bonus" in event:
                recovery[day] += event["recovery_bonus"]

        # Previous day coupling
        recovery[day] += 0.2 * sleep_quality[day-1] - 0.15 * activity_drive[day-1]

        # Clamp to valid range
        recovery[day] = np.clip(recovery[day], 0.3, 1.0)
        sleep_quality[day] = np.clip(sleep_quality[day], 0.3, 0.95)
        activity_drive[day] = np.clip(activity_drive[day], 0.3, 0.95)

    # Week-level trend: gradual improvement with dip in week 3
    trend = np.zeros(days)
    for day in range(days):
        if day < 7:
            trend[day] = 0
        elif day < 14:
            trend[day] = 0.05 * (day - 7) / 7
        elif day < 21:
            trend[day] = 0.05 - 0.08 * (day - 14) / 7
        else:
            trend[day] = -0.03 + 0.13 * (day - 21) / 7

    recovery += trend
    recovery = np.clip(recovery, 0.3, 1.0)

    return {
        "recovery": recovery,
        "sleep_quality": sleep_quality,
        "activity_drive": activity_drive,
    }


def generate_sleep_metrics(day: int, states: Dict[str, np.ndarray], start_date: datetime) -> Dict:
    """Generate daily_sleep.csv row for given day."""
    sq = states["sleep_quality"][day]
    weekday = day % 7

    # Bedtime and duration
    bedtime_hour = PERSONA["baseline_bedtime_hour"]
    if weekday in [5, 6]:
        bedtime_hour += 0.75
    if day in STORY_EVENTS and "bedtime_delay" in STORY_EVENTS[day]:
        bedtime_hour += STORY_EVENTS[day]["bedtime_delay"]

    bedtime_hour += np.random.normal(0, 0.3)
    bedtime = start_date + timedelta(days=day, hours=bedtime_hour)

    time_in_bed = 7.5 + sq * 1.5 + np.random.normal(0, 0.3)
    time_in_bed = np.clip(time_in_bed, 6.0, 9.5) * 3600

    waketime = bedtime + timedelta(seconds=time_in_bed)

    # Sleep stages
    efficiency = 0.75 + sq * 0.2 + np.random.normal(0, 0.03)
    efficiency = np.clip(efficiency, 0.7, 0.95)

    total_sleep = time_in_bed * efficiency
    latency = (1 - sq) * 600 + np.random.normal(0, 120)
    latency = max(60, min(latency, 1800))

    deep_pct = 0.12 + sq * 0.08 + np.random.normal(0, 0.02)
    rem_pct = 0.20 + sq * 0.08 + np.random.normal(0, 0.02)
    deep_pct = np.clip(deep_pct, 0.08, 0.25)
    rem_pct = np.clip(rem_pct, 0.15, 0.30)

    deep_sleep = total_sleep * deep_pct
    rem_sleep = total_sleep * rem_pct
    light_sleep = total_sleep - deep_sleep - rem_sleep
    awake_time = time_in_bed - total_sleep

    # Score and contributors (0-100 scale)
    score = int(50 + sq * 45 + np.random.normal(0, 3))
    score = np.clip(score, 50, 100)

    contributors = {
        "deep_sleep": int(70 + (deep_pct - 0.15) * 200 + np.random.normal(0, 5)),
        "efficiency": int(efficiency * 100 + np.random.normal(0, 3)),
        "latency": int(100 - (latency / 1800) * 30 + np.random.normal(0, 5)),
        "rem_sleep": int(70 + (rem_pct - 0.20) * 150 + np.random.normal(0, 5)),
        "restfulness": int(85 - awake_time / 3600 * 15 + np.random.normal(0, 5)),
        "timing": int(75 + sq * 20 + np.random.normal(0, 5)),
        "total_sleep": int(70 + (total_sleep / 3600 - 6.5) * 20 + np.random.normal(0, 5)),
    }

    for k in contributors:
        contributors[k] = np.clip(contributors[k], 50, 100)

    return {
        "id": str(uuid.uuid4()),
        "day": start_date.date() + timedelta(days=day),
        "score": score,
        "timestamp": waketime.isoformat(),
        "bedtime_start": bedtime.isoformat(),
        "bedtime_end": waketime.isoformat(),
        "time_in_bed": int(time_in_bed),
        "total_sleep_duration": int(total_sleep),
        "awake_time": int(awake_time),
        "deep_sleep_duration": int(deep_sleep),
        "light_sleep_duration": int(light_sleep),
        "rem_sleep_duration": int(rem_sleep),
        "latency": int(latency),
        "efficiency": round(efficiency, 3),
        "contributors": contributors,
    }


def generate_readiness_metrics(day: int, states: Dict[str, np.ndarray], sleep_metrics: List[Dict], start_date: datetime) -> Dict:
    """Generate daily_readiness.csv row for given day."""
    rec = states["recovery"][day]

    # HRV and RHR (inversely correlated with recovery)
    hrv = PERSONA["baseline_hrv"] + rec * 15 + np.random.normal(0, 3)
    rhr = PERSONA["baseline_rhr"] - rec * 8 + np.random.normal(0, 2)
    hrv = np.clip(hrv, 35, 75)
    rhr = np.clip(rhr, 48, 68)

    # Temperature (elevated when recovery is poor)
    temp_dev = PERSONA["baseline_temp"] - (rec - 0.7) * 0.4 + np.random.normal(0, 0.1)
    temp_dev = np.clip(temp_dev, -0.5, 0.5)

    # Score
    score = int(50 + rec * 45 + np.random.normal(0, 4))
    score = np.clip(score, 50, 100)

    # Contributors
    prev_sleep_score = sleep_metrics[day]["score"] if day < len(sleep_metrics) else 80
    prev_activity = states["activity_drive"][day-1] if day > 0 else 0.65

    contributors = {
        "activity_balance": int(75 + (0.65 - prev_activity) * 40 + np.random.normal(0, 5)),
        "body_temperature": int(85 - abs(temp_dev) * 60 + np.random.normal(0, 5)),
        "hrv_balance": int(60 + (hrv - 45) * 1.5 + np.random.normal(0, 5)),
        "previous_day_activity": int(70 - (prev_activity - 0.65) * 30 + np.random.normal(0, 5)),
        "previous_night": int(prev_sleep_score * 0.9 + np.random.normal(0, 3)),
        "recovery_index": int(50 + rec * 50 + np.random.normal(0, 5)),
        "resting_heart_rate": int(85 - (rhr - 52) * 2 + np.random.normal(0, 5)),
        "sleep_balance": int(75 + np.random.normal(0, 5)),
    }

    for k in contributors:
        contributors[k] = np.clip(contributors[k], 50, 100)

    timestamp = start_date + timedelta(days=day, hours=12)

    return {
        "id": str(uuid.uuid4()),
        "day": start_date.date() + timedelta(days=day),
        "score": score,
        "timestamp": timestamp.isoformat(),
        "temperature_deviation": round(temp_dev, 2),
        "temperature_trend_deviation": round(temp_dev * 0.8, 2),
        "contributors": contributors,
        "hrv": round(hrv, 1),
        "rhr": round(rhr, 1),
    }


def generate_activity_metrics(day: int, states: Dict[str, np.ndarray], start_date: datetime) -> Dict:
    """Generate daily_activity.csv row for given day."""
    ad = states["activity_drive"][day]
    weekday = day % 7

    # Steps and calories
    steps = PERSONA["baseline_steps"] + ad * 4000 + np.random.normal(0, 800)
    if weekday in [5, 6]:
        steps += 2000
    steps = int(np.clip(steps, 3000, 18000))

    active_cal = 300 + ad * 500 + np.random.normal(0, 80)
    active_cal = int(np.clip(active_cal, 200, 1200))
    total_cal = PERSONA["baseline_calories"] + int(active_cal * 0.5)

    # Activity time breakdown (seconds)
    high_time = ad * 3600 + np.random.normal(0, 600)
    medium_time = 2400 + ad * 1800 + np.random.normal(0, 400)
    low_time = 7200 + np.random.normal(0, 800)
    sedentary_time = 28800 - high_time - medium_time - low_time / 2 + np.random.normal(0, 1200)
    resting_time = 28800 + np.random.normal(0, 1200)
    non_wear_time = np.random.normal(900, 300)

    high_time = max(0, int(high_time))
    medium_time = max(0, int(medium_time))
    low_time = max(0, int(low_time))
    sedentary_time = max(0, int(sedentary_time))
    resting_time = max(0, int(resting_time))
    non_wear_time = max(0, int(non_wear_time))

    # MET and distance
    met_min = steps * 0.04 + high_time * 0.15
    distance = steps * 0.75  # meters
    target_cal = 500
    target_dist = 10000

    # Score
    score = int(50 + ad * 40 + np.random.normal(0, 5))
    score = np.clip(score, 45, 95)

    # Contributors
    contributors = {
        "meet_daily_targets": int(70 + (steps / 10000) * 25 + np.random.normal(0, 5)),
        "move_every_hour": int(75 + np.random.normal(0, 8)),
        "recovery_time": int(80 - ad * 20 + np.random.normal(0, 5)),
        "stay_active": int(65 + ad * 30 + np.random.normal(0, 5)),
        "training_frequency": int(70 + np.random.normal(0, 8)),
        "training_volume": int(60 + ad * 35 + np.random.normal(0, 5)),
    }

    for k in contributors:
        contributors[k] = np.clip(contributors[k], 50, 100)

    timestamp = start_date + timedelta(days=day, hours=23, minutes=59)

    return {
        "id": str(uuid.uuid4()),
        "day": start_date.date() + timedelta(days=day),
        "score": score,
        "timestamp": timestamp.isoformat(),
        "active_calories": active_cal,
        "total_calories": total_cal,
        "steps": steps,
        "high_activity_time": high_time,
        "medium_activity_time": medium_time,
        "low_activity_time": low_time,
        "sedentary_time": sedentary_time,
        "resting_time": resting_time,
        "non_wear_time": non_wear_time,
        "average_met_minutes": round(met_min, 1),
        "equivalent_walking_distance": int(distance),
        "target_calories": target_cal,
        "target_meters": target_dist,
        "meters_to_target": max(0, target_dist - int(distance)),
        "contributors": contributors,
    }


def generate_hypnogram(time_in_bed: int, sleep_quality: float, seed_offset: int) -> Tuple[str, Dict[str, int]]:
    """
    Generate hypnogram (5-min sleep phase string) using Markov chain.

    Returns:
        hypnogram string (e.g., "4443332221...")
        actual stage durations dict

    Codes: 1=deep, 2=light, 3=REM, 4=awake
    """
    np.random.seed(seed_offset)

    n_phases = int(time_in_bed / 300)
    phases = []

    # Initial state: light sleep after latency
    current = 2
    phases.append(4)  # Start awake (latency)

    for i in range(1, n_phases):
        # Time-dependent transitions
        progress = i / n_phases

        if progress < 0.33:  # First third: deep-heavy
            if current == 1:
                probs = [0.70, 0.25, 0.03, 0.02]
            elif current == 2:
                probs = [0.45, 0.50, 0.03, 0.02]
            elif current == 3:
                probs = [0.05, 0.45, 0.48, 0.02]
            else:  # awake
                probs = [0.05, 0.70, 0.05, 0.20]
        elif progress < 0.67:  # Middle: mixed
            if current == 1:
                probs = [0.65, 0.30, 0.03, 0.02]
            elif current == 2:
                probs = [0.15, 0.55, 0.28, 0.02]
            elif current == 3:
                probs = [0.05, 0.25, 0.68, 0.02]
            else:
                probs = [0.05, 0.70, 0.10, 0.15]
        else:  # Last third: REM-heavy
            if current == 1:
                probs = [0.50, 0.45, 0.03, 0.02]
            elif current == 2:
                probs = [0.05, 0.50, 0.43, 0.02]
            elif current == 3:
                probs = [0.02, 0.30, 0.66, 0.02]
            else:
                probs = [0.02, 0.60, 0.25, 0.13]

        # Sleep quality affects awake probability
        probs[3] *= (1.5 - sleep_quality)
        probs = np.array(probs)
        probs /= probs.sum()

        current = np.random.choice([1, 2, 3, 4], p=probs)
        phases.append(current)

    hypnogram = "".join(str(p) for p in phases)

    # Count actual durations
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for p in phases:
        counts[p] += 1

    durations = {
        "deep": counts[1] * 300,
        "light": counts[2] * 300,
        "rem": counts[3] * 300,
        "awake": counts[4] * 300,
    }

    return hypnogram, durations


def generate_heart_rate_series(hypnogram: str, baseline_rhr: float, seed_offset: int) -> str:
    """Generate 5-min interval heart rate series as JSON string."""
    np.random.seed(seed_offset)

    n_points = len(hypnogram)
    hr_values = []

    for i, phase in enumerate(hypnogram):
        # Base HR by sleep stage
        if phase == '1':  # deep
            base = baseline_rhr - 8
        elif phase == '2':  # light
            base = baseline_rhr - 3
        elif phase == '3':  # REM
            base = baseline_rhr + 2
        else:  # awake
            base = baseline_rhr + 8

        # U-shaped trend across night
        progress = i / n_points
        u_curve = (progress - 0.5) ** 2 * 10

        hr = base + u_curve + np.random.normal(0, 2)
        hr = int(np.clip(hr, 40, 85))
        hr_values.append(hr)

    return json.dumps({"interval": 300, "items": hr_values})


def generate_hrv_series(hypnogram: str, baseline_hrv: float, seed_offset: int) -> str:
    """Generate 5-min interval HRV series as JSON string (inversely correlated with HR)."""
    np.random.seed(seed_offset + 1)

    hrv_values = []

    for i, phase in enumerate(hypnogram):
        # Base HRV by sleep stage (inverse of HR pattern)
        if phase == '1':  # deep
            base = baseline_hrv + 15
        elif phase == '2':  # light
            base = baseline_hrv + 5
        elif phase == '3':  # REM
            base = baseline_hrv - 3
        else:  # awake
            base = baseline_hrv - 8

        # Inverse U-shaped trend
        progress = i / len(hypnogram)
        inv_u_curve = -((progress - 0.5) ** 2) * 20

        hrv = base + inv_u_curve + np.random.normal(0, 3)
        hrv = int(np.clip(hrv, 20, 90))
        hrv_values.append(hrv)

    return json.dumps({"interval": 300, "items": hrv_values})


def generate_movement_series(hypnogram: str, seed_offset: int) -> str:
    """Generate 30-sec interval movement series as digit string."""
    np.random.seed(seed_offset + 2)

    # 10 movement samples per hypnogram phase (5min / 30sec = 10)
    movement = []

    for phase in hypnogram:
        # Movement level by sleep stage
        if phase == '1':  # deep
            base_movement = 0.05
        elif phase == '2':  # light
            base_movement = 0.15
        elif phase == '3':  # REM
            base_movement = 0.10
        else:  # awake
            base_movement = 0.40

        for _ in range(10):
            level = int(np.random.exponential(base_movement) * 10)
            level = min(level, 9)
            movement.append(str(level))

    return "".join(movement)


def generate_sleep_detail(sleep_metrics: Dict, day: int, readiness_metrics: Dict) -> Dict:
    """Generate sleep.csv row with detailed interval data."""
    # Generate hypnogram and recompute durations
    hypnogram, actual_durations = generate_hypnogram(
        sleep_metrics["time_in_bed"],
        sleep_metrics["score"] / 100.0,
        day * 1000
    )

    # Override with actual durations from hypnogram
    sleep_metrics["deep_sleep_duration"] = actual_durations["deep"]
    sleep_metrics["light_sleep_duration"] = actual_durations["light"]
    sleep_metrics["rem_sleep_duration"] = actual_durations["rem"]
    sleep_metrics["awake_time"] = actual_durations["awake"]
    sleep_metrics["total_sleep_duration"] = (
        actual_durations["deep"] + actual_durations["light"] + actual_durations["rem"]
    )
    sleep_metrics["efficiency"] = sleep_metrics["total_sleep_duration"] / sleep_metrics["time_in_bed"]

    # Generate interval series
    hr_json = generate_heart_rate_series(hypnogram, readiness_metrics["rhr"], day * 1000 + 1)
    hrv_json = generate_hrv_series(hypnogram, readiness_metrics["hrv"], day * 1000 + 2)
    movement_str = generate_movement_series(hypnogram, day * 1000 + 3)

    # Calculate summary stats
    hr_items = json.loads(hr_json)["items"]
    hrv_items = json.loads(hrv_json)["items"]

    return {
        "id": sleep_metrics["id"],
        "day": sleep_metrics["day"],
        "bedtime_start": sleep_metrics["bedtime_start"],
        "bedtime_end": sleep_metrics["bedtime_end"],
        "average_breath": round(14.5 + np.random.normal(0, 0.5), 1),
        "average_heart_rate": round(np.mean(hr_items), 1),
        "average_hrv": round(np.mean(hrv_items), 1),
        "awake_time": sleep_metrics["awake_time"],
        "deep_sleep_duration": sleep_metrics["deep_sleep_duration"],
        "efficiency": round(sleep_metrics["efficiency"], 3),
        "latency": sleep_metrics["latency"],
        "light_sleep_duration": sleep_metrics["light_sleep_duration"],
        "lowest_heart_rate": int(min(hr_items)),
        "rem_sleep_duration": sleep_metrics["rem_sleep_duration"],
        "restless_periods": int(movement_str.count('5') + movement_str.count('6') +
                               movement_str.count('7') + movement_str.count('8') +
                               movement_str.count('9')),
        "time_in_bed": sleep_metrics["time_in_bed"],
        "total_sleep_duration": sleep_metrics["total_sleep_duration"],
        "type": "long_sleep",
        "period": 0,
        "sleep_phase_5_min": hypnogram,
        "movement_30_sec": movement_str,
        "heart_rate": hr_json,
        "hrv": hrv_json,
    }


def write_csvs(sleep_data: List[Dict], readiness_data: List[Dict],
               activity_data: List[Dict], sleep_detail_data: List[Dict],
               output_dir: str):
    """Write all 4 CSV files with exact Oura column format."""
    os.makedirs(output_dir, exist_ok=True)

    # daily_sleep.csv
    with open(os.path.join(output_dir, "daily_sleep.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "day", "score", "timestamp",
            "contributors.deep_sleep", "contributors.efficiency", "contributors.latency",
            "contributors.rem_sleep", "contributors.restfulness", "contributors.timing",
            "contributors.total_sleep"
        ])
        writer.writeheader()
        for row in sleep_data:
            writer.writerow({
                "id": row["id"],
                "day": row["day"],
                "score": row["score"],
                "timestamp": row["timestamp"],
                "contributors.deep_sleep": row["contributors"]["deep_sleep"],
                "contributors.efficiency": row["contributors"]["efficiency"],
                "contributors.latency": row["contributors"]["latency"],
                "contributors.rem_sleep": row["contributors"]["rem_sleep"],
                "contributors.restfulness": row["contributors"]["restfulness"],
                "contributors.timing": row["contributors"]["timing"],
                "contributors.total_sleep": row["contributors"]["total_sleep"],
            })

    # daily_readiness.csv
    with open(os.path.join(output_dir, "daily_readiness.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "day", "score", "timestamp", "temperature_deviation", "temperature_trend_deviation",
            "contributors.activity_balance", "contributors.body_temperature", "contributors.hrv_balance",
            "contributors.previous_day_activity", "contributors.previous_night",
            "contributors.recovery_index", "contributors.resting_heart_rate", "contributors.sleep_balance"
        ])
        writer.writeheader()
        for row in readiness_data:
            writer.writerow({
                "id": row["id"],
                "day": row["day"],
                "score": row["score"],
                "timestamp": row["timestamp"],
                "temperature_deviation": row["temperature_deviation"],
                "temperature_trend_deviation": row["temperature_trend_deviation"],
                "contributors.activity_balance": row["contributors"]["activity_balance"],
                "contributors.body_temperature": row["contributors"]["body_temperature"],
                "contributors.hrv_balance": row["contributors"]["hrv_balance"],
                "contributors.previous_day_activity": row["contributors"]["previous_day_activity"],
                "contributors.previous_night": row["contributors"]["previous_night"],
                "contributors.recovery_index": row["contributors"]["recovery_index"],
                "contributors.resting_heart_rate": row["contributors"]["resting_heart_rate"],
                "contributors.sleep_balance": row["contributors"]["sleep_balance"],
            })

    # daily_activity.csv
    with open(os.path.join(output_dir, "daily_activity.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "day", "score", "timestamp", "active_calories", "total_calories", "steps",
            "high_activity_time", "medium_activity_time", "low_activity_time",
            "sedentary_time", "resting_time", "non_wear_time",
            "average_met_minutes", "equivalent_walking_distance", "target_calories",
            "target_meters", "meters_to_target",
            "contributors.meet_daily_targets", "contributors.move_every_hour",
            "contributors.recovery_time", "contributors.stay_active",
            "contributors.training_frequency", "contributors.training_volume"
        ])
        writer.writeheader()
        for row in activity_data:
            writer.writerow({
                "id": row["id"],
                "day": row["day"],
                "score": row["score"],
                "timestamp": row["timestamp"],
                "active_calories": row["active_calories"],
                "total_calories": row["total_calories"],
                "steps": row["steps"],
                "high_activity_time": row["high_activity_time"],
                "medium_activity_time": row["medium_activity_time"],
                "low_activity_time": row["low_activity_time"],
                "sedentary_time": row["sedentary_time"],
                "resting_time": row["resting_time"],
                "non_wear_time": row["non_wear_time"],
                "average_met_minutes": row["average_met_minutes"],
                "equivalent_walking_distance": row["equivalent_walking_distance"],
                "target_calories": row["target_calories"],
                "target_meters": row["target_meters"],
                "meters_to_target": row["meters_to_target"],
                "contributors.meet_daily_targets": row["contributors"]["meet_daily_targets"],
                "contributors.move_every_hour": row["contributors"]["move_every_hour"],
                "contributors.recovery_time": row["contributors"]["recovery_time"],
                "contributors.stay_active": row["contributors"]["stay_active"],
                "contributors.training_frequency": row["contributors"]["training_frequency"],
                "contributors.training_volume": row["contributors"]["training_volume"],
            })

    # sleep.csv
    with open(os.path.join(output_dir, "sleep.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "id", "day", "bedtime_start", "bedtime_end", "average_breath",
            "average_heart_rate", "average_hrv", "awake_time", "deep_sleep_duration",
            "efficiency", "latency", "light_sleep_duration", "lowest_heart_rate",
            "rem_sleep_duration", "restless_periods", "time_in_bed", "total_sleep_duration",
            "type", "period", "sleep_phase_5_min", "movement_30_sec", "heart_rate", "hrv"
        ])
        writer.writeheader()
        writer.writerows(sleep_detail_data)

    print(f"✓ Generated 4 CSV files in {output_dir}/")
    print(f"  - daily_sleep.csv: {len(sleep_data)} rows")
    print(f"  - daily_readiness.csv: {len(readiness_data)} rows")
    print(f"  - daily_activity.csv: {len(activity_data)} rows")
    print(f"  - sleep.csv: {len(sleep_detail_data)} rows")


def main():
    parser = argparse.ArgumentParser(description="Generate mock Oura Ring CSV data")
    parser.add_argument("--days", type=int, default=30, help="Number of days to generate")
    parser.add_argument("--start-date", type=str, default="2025-01-01",
                       help="Start date (YYYY-MM-DD)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--output-dir", type=str, default="data/raw/oura_export_mock",
                       help="Output directory")

    args = parser.parse_args()

    start_date = datetime.fromisoformat(args.start_date).replace(tzinfo=timezone.utc)

    print(f"Generating {args.days} days of mock Oura data...")
    print(f"Start date: {args.start_date}")
    print(f"Random seed: {args.seed}")
    print()

    # Generate latent states
    states = generate_latent_states(args.days, args.seed)

    # Generate daily metrics
    sleep_data = []
    readiness_data = []
    activity_data = []
    sleep_detail_data = []

    for day in range(args.days):
        sleep = generate_sleep_metrics(day, states, start_date)
        sleep_data.append(sleep)

        readiness = generate_readiness_metrics(day, states, sleep_data, start_date)
        readiness_data.append(readiness)

        activity = generate_activity_metrics(day, states, start_date)
        activity_data.append(activity)

        sleep_detail = generate_sleep_detail(sleep, day, readiness)
        sleep_detail_data.append(sleep_detail)

    # Write CSVs
    write_csvs(sleep_data, readiness_data, activity_data, sleep_detail_data, args.output_dir)

    # Summary stats
    print()
    print("Summary Statistics:")
    print(f"  Sleep scores: {min(s['score'] for s in sleep_data)}-{max(s['score'] for s in sleep_data)}")
    print(f"  Readiness scores: {min(r['score'] for r in readiness_data)}-{max(r['score'] for r in readiness_data)}")
    print(f"  Activity scores: {min(a['score'] for a in activity_data)}-{max(a['score'] for a in activity_data)}")
    print()
    print(f"Day {args.days-1} (latest):")
    print(f"  Sleep: {sleep_data[-1]['score']}, Readiness: {readiness_data[-1]['score']}, Activity: {activity_data[-1]['score']}")
    print(f"  HRV: {readiness_data[-1]['hrv']}ms, RHR: {readiness_data[-1]['rhr']}bpm")


if __name__ == "__main__":
    main()
