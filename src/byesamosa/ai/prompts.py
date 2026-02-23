"""Prompt templates for Claude API integration.

Builds structured prompts from user data to generate personalized insights.
"""

import json
from typing import Any


SYSTEM_PROMPT = """You are a personal sleep and recovery analyst for an Oura Ring user. Your role is to analyze their biometric data and provide actionable insights that go beyond generic advice.

Your responsibilities:
1. Analyze sleep, readiness, and activity scores along with their underlying contributors
2. Provide reasoning chains that connect observations to physiological causes to actionable implications
3. Generate specific, personalized recommendations (not generic sleep hygiene)
4. Label contributors using their ACTUAL values from the data:
   - "boost" (>=85): factors that helped the score
   - "ok" (75-84): factors that were acceptable
   - "drag" (<75): factors that hurt the score
5. Create personalized "good looks like" benchmarks based on the user's historical baseline data
6. Return structured JSON matching the AIInsight schema

Guidelines for insights:
- Be specific: reference actual numbers from the data
- Connect dots: don't just state observations, explain the physiological why
- Be actionable: give concrete next steps, not platitudes
- Personalize benchmarks: use the user's 30-day averages, not generic targets
- Prioritize: focus on the biggest opportunities for improvement
- Use ACTUAL contributor values from the data, do NOT estimate or make up values

Example reasoning chain pattern:
- Observation: "Your HRV dropped 15ms below your 30-day average (48 vs 63ms)"
- Cause: "This indicates elevated sympathetic nervous system activity, likely from incomplete recovery"
- So what: "Your body needs more recovery time before high-intensity training"

Example action item:
- Title: "Skip the high-intensity workout today"
- Detail: "HRV 48ms (24% below baseline) + readiness 67 = incomplete recovery. Do zone 2 cardio instead."
- Priority: "high"
- Tag: "Prevent injury"

Return your response as valid JSON matching the AIInsight schema."""


def build_user_prompt(
    latest: dict,
    baselines: dict,
    trends_7d: dict,
    has_sleep_phases: bool = False,
) -> str:
    """Build the user prompt with data context for Claude.

    Args:
        latest: Latest day's data from get_latest_day()
        baselines: Baseline statistics for all metrics (7d/30d/90d)
        trends_7d: Last 7 days of score trends from get_trends()
        has_sleep_phases: Whether 5-min interval sleep phase data is available

    Returns:
        Formatted prompt string with data sections
    """
    # Extract data
    day = latest.get("day")
    sleep = latest.get("sleep", {})
    readiness = latest.get("readiness", {})
    activity = latest.get("activity", {})
    stress = latest.get("stress")
    spo2 = latest.get("spo2")
    cardiovascular_age = latest.get("cardiovascular_age")

    # Build prompt sections
    sections = []

    # Header
    sections.append(f"# Data Analysis Request for {day}")
    sections.append("")
    sections.append(
        "Analyze the following Oura Ring data and generate personalized insights."
    )
    sections.append("")

    # Latest scores section
    sections.append("## Latest Day Scores")
    sections.append(f"Date: {day}")
    sections.append("")
    sections.append(f"**Sleep Score:** {sleep.get('score', 'N/A')}")
    sections.append(
        f"**Readiness Score:** {readiness.get('score', 'N/A') if readiness else 'N/A'}"
    )
    sections.append(
        f"**Activity Score:** {activity.get('score', 'N/A') if activity else 'N/A'}"
    )
    sections.append("")

    # Sleep metrics
    sections.append("## Sleep Metrics")
    total_sleep_hours = (
        sleep.get("total_sleep_duration", 0) / 3600
        if sleep.get("total_sleep_duration")
        else 0
    )
    rem_sleep_hours = (
        sleep.get("rem_sleep_duration", 0) / 3600
        if sleep.get("rem_sleep_duration")
        else 0
    )
    deep_sleep_hours = (
        sleep.get("deep_sleep_duration", 0) / 3600
        if sleep.get("deep_sleep_duration")
        else 0
    )
    light_sleep_hours = (
        sleep.get("light_sleep_duration", 0) / 3600
        if sleep.get("light_sleep_duration")
        else 0
    )

    sections.append(f"- Total Sleep: {total_sleep_hours:.1f}h")
    sections.append(
        f"- REM Sleep: {rem_sleep_hours:.1f}h"
        f" ({rem_sleep_hours / total_sleep_hours * 100 if total_sleep_hours > 0 else 0:.0f}%)"
    )
    sections.append(
        f"- Deep Sleep: {deep_sleep_hours:.1f}h"
        f" ({deep_sleep_hours / total_sleep_hours * 100 if total_sleep_hours > 0 else 0:.0f}%)"
    )
    sections.append(
        f"- Light Sleep: {light_sleep_hours:.1f}h"
        f" ({light_sleep_hours / total_sleep_hours * 100 if total_sleep_hours > 0 else 0:.0f}%)"
    )
    sections.append(f"- Efficiency: {sleep.get('efficiency', 'N/A')}%")
    sections.append(f"- HRV: {sleep.get('average_hrv', 'N/A')}ms")
    sections.append(
        f"- Resting Heart Rate: {sleep.get('lowest_heart_rate', 'N/A')}bpm"
    )
    sections.append(
        f"- Average Heart Rate: {sleep.get('average_heart_rate', 'N/A')}bpm"
    )
    sections.append(
        f"- Average Breath: {sleep.get('average_breath', 'N/A')} breaths/min"
    )
    sections.append(
        f"- Temperature Deviation: {sleep.get('temperature_deviation', 'N/A')}°C"
    )
    time_in_bed_hours = (
        sleep.get("time_in_bed", 0) / 3600 if sleep.get("time_in_bed") else 0
    )
    sections.append(f"- Time in Bed: {time_in_bed_hours:.1f}h")
    sections.append(f"- Restless Periods: {sleep.get('restless_periods', 'N/A')}")
    sections.append("")

    # Sleep contributors
    sleep_contribs = sleep.get("contributors")
    if sleep_contribs:
        sections.append("## Sleep Score Contributors")
        for name, value in sleep_contribs.items():
            if value is not None:
                label = name.replace("_", " ").title()
                tag = "boost" if value >= 85 else ("ok" if value >= 75 else "drag")
                sections.append(f"- {label}: {value} ({tag})")
        sections.append("")

    # Readiness contributors
    if readiness:
        sections.append("## Readiness Metrics")
        sections.append(
            f"- Temperature Deviation: {readiness.get('temperature_deviation', 'N/A')}°C"
        )
        sections.append(
            f"- Temperature Trend Deviation: {readiness.get('temperature_trend_deviation', 'N/A')}°C"
        )
        sections.append("")

        readiness_contribs = readiness.get("contributors")
        if readiness_contribs:
            sections.append("## Readiness Score Contributors")
            for name, value in readiness_contribs.items():
                if value is not None:
                    label = name.replace("_", " ").title()
                    tag = "boost" if value >= 85 else ("ok" if value >= 75 else "drag")
                    sections.append(f"- {label}: {value} ({tag})")
            sections.append("")

    # Activity metrics
    if activity:
        sections.append("## Activity Metrics")
        steps = activity.get("steps")
        sections.append(f"- Steps: {steps:,}" if isinstance(steps, int) else f"- Steps: {steps}")
        sections.append(f"- Active Calories: {activity.get('active_calories', 'N/A')}")
        sections.append(f"- Total Calories: {activity.get('total_calories', 'N/A')}")
        eq_dist = activity.get("equivalent_walking_distance")
        if eq_dist is not None:
            sections.append(f"- Equivalent Walking Distance: {eq_dist}m")
        sections.append("")

        # Activity contributors
        activity_contribs = activity.get("contributors")
        if activity_contribs:
            sections.append("## Activity Score Contributors")
            for name, value in activity_contribs.items():
                if value is not None:
                    label = name.replace("_", " ").title()
                    tag = "boost" if value >= 85 else ("ok" if value >= 75 else "drag")
                    sections.append(f"- {label}: {value} ({tag})")
            sections.append("")

    # Stress data
    if stress:
        sections.append("## Stress")
        sections.append(f"- Day Summary: {stress.get('day_summary', 'N/A')}")
        sections.append(f"- Recovery High: {stress.get('recovery_high', 'N/A')} min")
        sections.append(f"- Stress High: {stress.get('stress_high', 'N/A')} min")
        sections.append("")

    # SpO2 data
    if spo2:
        sections.append("## Blood Oxygen (SpO2)")
        sections.append(f"- Average SpO2: {spo2.get('spo2_average', 'N/A')}%")
        sections.append(
            f"- Breathing Disturbance Index: {spo2.get('breathing_disturbance_index', 'N/A')}"
        )
        sections.append("")

    # Cardiovascular age
    if cardiovascular_age:
        sections.append("## Cardiovascular Age")
        sections.append(
            f"- Vascular Age: {cardiovascular_age.get('vascular_age', 'N/A')}"
        )
        sections.append("")

    # Baselines section
    sections.append("## Your Baseline Statistics")
    sections.append("")
    sections.append("For context, here are your rolling averages:")
    sections.append("")

    # Key metrics baselines
    key_metrics = [
        ("sleep_score", "Sleep Score"),
        ("readiness_score", "Readiness Score"),
        ("activity_score", "Activity Score"),
        ("average_hrv", "HRV"),
        ("lowest_heart_rate", "Resting Heart Rate"),
        ("total_sleep_duration", "Total Sleep"),
        ("deep_sleep_duration", "Deep Sleep"),
        ("rem_sleep_duration", "REM Sleep"),
        ("efficiency", "Sleep Efficiency"),
    ]

    for metric_key, metric_label in key_metrics:
        metric_baselines = baselines.get(metric_key, {})
        if metric_baselines:
            avg_7d = metric_baselines.get("avg_7d")
            avg_30d = metric_baselines.get("avg_30d")
            avg_90d = metric_baselines.get("avg_90d")
            std_30d = metric_baselines.get("std_30d")

            # Format based on metric type
            if "duration" in metric_key:
                avg_7d = f"{avg_7d / 3600:.1f}h" if avg_7d else "N/A"
                avg_30d = f"{avg_30d / 3600:.1f}h" if avg_30d else "N/A"
                avg_90d = f"{avg_90d / 3600:.1f}h" if avg_90d else "N/A"
            elif metric_key == "efficiency":
                avg_7d = f"{avg_7d:.0f}%" if avg_7d else "N/A"
                avg_30d = f"{avg_30d:.0f}%" if avg_30d else "N/A"
                avg_90d = f"{avg_90d:.0f}%" if avg_90d else "N/A"
            else:
                avg_7d = f"{avg_7d:.1f}" if avg_7d else "N/A"
                avg_30d = f"{avg_30d:.1f}" if avg_30d else "N/A"
                avg_90d = f"{avg_90d:.1f}" if avg_90d else "N/A"

            sections.append(
                f"**{metric_label}:** 7d avg: {avg_7d}, 30d avg: {avg_30d}, 90d avg: {avg_90d}"
            )
            if std_30d:
                sections.append(f"  (30d std dev: {std_30d:.1f})")

    sections.append("")

    # 7-day trends
    sections.append("## Recent Trends (Last 7 Days)")
    sections.append("")

    for score_type in ["sleep_score", "readiness_score", "activity_score"]:
        trend_data = trends_7d.get(score_type, [])
        if trend_data:
            values = [d["value"] for d in trend_data if d.get("value") is not None]
            if values:
                label = score_type.replace("_", " ").title()
                trend_str = ", ".join(str(v) for v in values)
                sections.append(f"**{label}:** {trend_str}")

    sections.append("")

    # Output requirements
    sections.append("## Required Output Format")
    sections.append("")
    sections.append("Generate a complete AIInsight JSON object with:")
    sections.append("")
    sections.append("1. **score_insights**: For each score type (sleep, readiness, activity):")
    sections.append("   - one_liner: Brief summary of what drove the score")
    sections.append(
        "   - contributors: Array of ContributorLabel objects (name, value 0-100, tag)"
    )
    sections.append(
        "     - Tag as 'boost' (>=85), 'ok' (75-84), or 'drag' (<75)"
    )
    sections.append(
        "     - Use the ACTUAL contributor values from the data above — do NOT estimate or make up values"
    )
    sections.append(
        "     - For sleep: use contributors like 'Deep Sleep', 'Efficiency', 'Latency',"
        " 'Rem Sleep', 'Restfulness', 'Timing', 'Total Sleep'"
    )
    sections.append(
        "     - For readiness: use 'Activity Balance', 'Body Temperature', 'Hrv Balance',"
        " 'Previous Day Activity', 'Previous Night', 'Recovery Index',"
        " 'Resting Heart Rate', 'Sleep Balance', 'Sleep Regularity'"
    )
    sections.append(
        "     - For activity: use 'Meet Daily Targets', 'Move Every Hour',"
        " 'Recovery Time', 'Stay Active', 'Training Frequency', 'Training Volume'"
    )
    sections.append("")
    sections.append("2. **reasoning_chain**: Exactly 3 steps:")
    sections.append("   - Step 1 label='Observation': What stands out in the data?")
    sections.append("   - Step 2 label='Cause': What's the physiological explanation?")
    sections.append("   - Step 3 label='So what': What does this mean for the user?")
    sections.append("")
    sections.append("3. **actions**: 3-4 specific action items:")
    sections.append(
        "   - Priority: 'high' for critical items, 'medium' for beneficial, 'low' for optional"
    )
    sections.append("   - Tag: Category like 'Fix REM', 'Prevent injury', 'Optimize performance'")
    sections.append("")
    sections.append("4. **vital_annotations**: Context for each vital:")
    sections.append(
        "   - Keys: 'hrv', 'rhr', 'temp', 'breath' (even if breath data not available, provide annotation)"
    )
    sections.append("   - Each value: ChartAnnotation with 'text' field")
    sections.append("")
    sections.append("5. **trend_annotations**: Insights for trend charts:")
    sections.append("   - Keys: 'sleep_score', 'hrv_rhr'")
    sections.append("   - Each value: TrendAnnotation with 'icon' (up/down/heart) and 'text'")
    sections.append("")
    sections.append("6. **good_looks_like**: Personalized benchmarks based on user's data:")
    sections.append("   - Keys: 'sleep', 'readiness', 'activity'")
    sections.append(
        "   - Each value: Description of what a good day looks like for THIS user"
    )
    sections.append(
        "   - Example: 'All contributors >=80, total sleep >=7.5h, efficiency >=90%'"
    )
    sections.append("")

    if has_sleep_phases:
        sections.append(
            "7. **hypnogram_annotation**: Optional ChartAnnotation for sleep stage visualization"
        )
        sections.append(
            "   - Provide insight about sleep architecture (REM cycles, deep sleep timing, etc.)"
        )
        sections.append("")

    sections.append("Return ONLY valid JSON. No markdown formatting, no code blocks.")

    return "\n".join(sections)


def format_baselines_for_prompt(baselines_list: list[dict]) -> dict[str, dict]:
    """Convert list of baseline records to a metrics-first dict.

    Args:
        baselines_list: List of Baseline dicts from baselines.json

    Returns:
        Dict keyed by metric name, values are baseline stats
        Example: {"sleep_score": {"avg_7d": 85.0, "avg_30d": 83.2, ...}, ...}
    """
    result = {}

    for baseline in baselines_list:
        metric = baseline.get("metric")
        if metric:
            if metric not in result:
                result[metric] = {}

            result[metric] = {
                "avg_7d": baseline.get("avg_7d"),
                "avg_30d": baseline.get("avg_30d"),
                "avg_90d": baseline.get("avg_90d"),
                "std_30d": baseline.get("std_30d"),
            }

    return result
