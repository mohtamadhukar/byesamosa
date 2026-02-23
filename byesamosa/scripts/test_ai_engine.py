"""Test script for AI engine with mock data.

Verifies that the AI engine can generate insights from mock data.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from byesamosa.ai.engine import generate_insight, cache_insight, log_api_cost
from byesamosa.ai.prompts import format_baselines_for_prompt
from byesamosa.config import Settings
from byesamosa.data.store import DataStore
from byesamosa.data.queries import get_latest_day, get_trends, has_sleep_phases
from datetime import datetime


def main():
    """Test the AI engine with mock data."""
    print("=" * 60)
    print("AI Engine Test with Mock Data")
    print("=" * 60)
    print()

    # Load settings
    try:
        settings = Settings()
        print("✓ Settings loaded")
    except Exception as e:
        print(f"✗ Failed to load settings: {e}")
        print("\nMake sure you have a .env file with ANTHROPIC_API_KEY")
        return 1

    # Initialize data store
    data_dir = Path("data")
    store = DataStore(data_dir)
    print("✓ DataStore initialized")

    # Load latest day
    print("\nLoading mock data...")
    latest = get_latest_day(store)
    if not latest:
        print("✗ No data found - run scripts/generate_mock_json.py first")
        return 1

    print(f"✓ Latest day: {latest['day']}")
    print(f"  Sleep score: {latest['sleep']['sleep_score']}")
    print(f"  Readiness score: {latest['readiness']['readiness_score'] if latest['readiness'] else 'N/A'}")
    print(f"  Activity score: {latest['activity']['activity_score'] if latest['activity'] else 'N/A'}")

    # Load baselines
    baselines_file = data_dir / "processed" / "baselines.json"
    if not baselines_file.exists():
        print("\n✗ Baselines not found - run compute_baselines() first")
        return 1

    with open(baselines_file) as f:
        baselines_list = json.load(f)

    # Filter baselines for latest day
    latest_day = latest["day"]
    latest_baselines = [b for b in baselines_list if b["day"] == str(latest_day)]

    # Format baselines for prompt
    baselines = format_baselines_for_prompt(latest_baselines)
    print(f"✓ Loaded {len(baselines)} baseline metrics")

    # Load trends
    trends_7d = {}
    for metric in ["sleep_score", "readiness_score", "activity_score"]:
        trends_7d[metric] = get_trends(store, metric, days=7)
    print(f"✓ Loaded 7-day trends")

    # Check sleep phases
    has_phases = has_sleep_phases(store)
    print(f"✓ Sleep phase data available: {has_phases}")

    # Generate insight
    print("\n" + "=" * 60)
    print("Calling Claude API...")
    print("=" * 60)
    print()

    try:
        insight = generate_insight(
            latest=latest,
            baselines=baselines,
            trends_7d=trends_7d,
            has_sleep_phases=has_phases,
            settings=settings,
        )

        print("✓ Insight generated successfully!")
        print()

        # Display key parts of insight
        print("=" * 60)
        print("Generated Insight Summary")
        print("=" * 60)
        print()

        print("SCORE INSIGHTS:")
        print("-" * 60)
        for score_type, score_insight in insight.score_insights.items():
            print(f"\n{score_type.upper()}:")
            print(f"  One-liner: {score_insight.one_liner}")
            print(f"  Contributors ({len(score_insight.contributors)}):")
            for contrib in score_insight.contributors:
                print(f"    - {contrib.name}: {contrib.value} [{contrib.tag}]")

        print("\n" + "=" * 60)
        print("REASONING CHAIN:")
        print("-" * 60)
        for i, step in enumerate(insight.reasoning_chain, 1):
            print(f"\n{i}. {step.label}")
            print(f"   {step.text}")

        print("\n" + "=" * 60)
        print("ACTION ITEMS:")
        print("-" * 60)
        for i, action in enumerate(insight.actions, 1):
            print(f"\n{i}. [{action.priority.upper()}] {action.title}")
            print(f"   {action.detail}")
            print(f"   Tag: {action.tag}")

        print("\n" + "=" * 60)
        print("VITAL ANNOTATIONS:")
        print("-" * 60)
        for vital, annotation in insight.vital_annotations.items():
            print(f"  {vital.upper()}: {annotation.text}")

        print("\n" + "=" * 60)
        print("TREND ANNOTATIONS:")
        print("-" * 60)
        for trend, annotation in insight.trend_annotations.items():
            print(f"  {trend}: [{annotation.icon}] {annotation.text}")

        print("\n" + "=" * 60)
        print("GOOD LOOKS LIKE:")
        print("-" * 60)
        for score_type, benchmark in insight.good_looks_like.items():
            print(f"  {score_type.upper()}: {benchmark}")

        if insight.hypnogram_annotation:
            print("\n" + "=" * 60)
            print("HYPNOGRAM ANNOTATION:")
            print("-" * 60)
            print(f"  {insight.hypnogram_annotation.text}")

        # Cache the insight
        print("\n" + "=" * 60)
        print("Caching insight...")
        print("=" * 60)
        cache_insight(insight, data_dir)
        print(f"✓ Insight cached to data/insights/{insight.date}.json")

        # Log cost (estimate)
        print("\nLogging API cost...")
        estimated_cost = 0.05  # Approximate cost with max_tokens=4096
        log_api_cost(data_dir, datetime.now(), estimated_cost)
        print(f"✓ Logged estimated cost: ${estimated_cost:.2f}")

        print("\n" + "=" * 60)
        print("✓ AI Engine Test Complete!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n✗ Failed to generate insight: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
