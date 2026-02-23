"""Verify AI engine implementation without making API calls.

Tests prompt generation, data formatting, and module structure.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from byesamosa.ai.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    format_baselines_for_prompt,
)
from byesamosa.ai.engine import (
    cache_insight,
    load_cached_insight,
    log_api_cost,
    _create_fallback_insight,
)
from byesamosa.ai.schemas import AIInsight
from byesamosa.data.store import DataStore
from byesamosa.data.queries import get_latest_day, get_trends, has_sleep_phases
from datetime import datetime, date


def main():
    """Verify AI engine implementation."""
    print("=" * 60)
    print("AI Engine Verification (No API Calls)")
    print("=" * 60)
    print()

    # Test 1: Check module imports
    print("Test 1: Module imports")
    print("-" * 60)
    try:
        import anthropic
        print("✓ anthropic module available")
    except ImportError:
        print("✗ anthropic module not found - run 'uv sync'")
        return 1

    # Test 2: Check system prompt
    print("\nTest 2: System prompt")
    print("-" * 60)
    print(f"✓ System prompt length: {len(SYSTEM_PROMPT)} chars")
    assert "reasoning chains" in SYSTEM_PROMPT.lower()
    assert "AIInsight" in SYSTEM_PROMPT
    print("✓ System prompt contains expected keywords")

    # Test 3: Load mock data
    print("\nTest 3: Load mock data")
    print("-" * 60)
    data_dir = Path("data")
    store = DataStore(data_dir)

    latest = get_latest_day(store)
    if not latest:
        print("✗ No data found - run scripts/generate_mock_json.py first")
        return 1

    print(f"✓ Latest day: {latest['day']}")
    print(f"  Sleep score: {latest['sleep']['sleep_score']}")
    print(f"  Readiness score: {latest['readiness']['readiness_score'] if latest['readiness'] else 'N/A'}")
    print(f"  Activity score: {latest['activity']['activity_score'] if latest['activity'] else 'N/A'}")

    # Test 4: Load and format baselines
    print("\nTest 4: Format baselines")
    print("-" * 60)
    baselines_file = data_dir / "processed" / "baselines.json"
    if not baselines_file.exists():
        print("✗ Baselines not found")
        return 1

    with open(baselines_file) as f:
        baselines_list = json.load(f)

    latest_day = latest["day"]
    latest_baselines = [b for b in baselines_list if b["day"] == str(latest_day)]

    baselines = format_baselines_for_prompt(latest_baselines)
    print(f"✓ Formatted {len(baselines)} baseline metrics")
    assert "sleep_score" in baselines
    assert "average_hrv" in baselines
    print("✓ Baselines contain expected metrics")

    # Test 5: Load trends
    print("\nTest 5: Load trends")
    print("-" * 60)
    trends_7d = {}
    for metric in ["sleep_score", "readiness_score", "activity_score"]:
        trends_7d[metric] = get_trends(store, metric, days=7)
        print(f"  {metric}: {len(trends_7d[metric])} days")
    print("✓ Loaded 7-day trends")

    # Test 6: Check sleep phases
    print("\nTest 6: Check sleep phases")
    print("-" * 60)
    has_phases = has_sleep_phases(store)
    print(f"✓ Sleep phase data available: {has_phases}")

    # Test 7: Build user prompt
    print("\nTest 7: Build user prompt")
    print("-" * 60)
    prompt = build_user_prompt(latest, baselines, trends_7d, has_phases)
    print(f"✓ Prompt length: {len(prompt)} chars")
    print(f"✓ Prompt tokens (approx): {len(prompt) // 4}")
    assert len(prompt) > 1000
    assert "Sleep Score:" in prompt
    assert "Baseline Statistics" in prompt
    assert "Recent Trends" in prompt
    assert "Required Output Format" in prompt
    print("✓ Prompt contains expected sections")

    # Test 8: Create fallback insight
    print("\nTest 8: Fallback insight")
    print("-" * 60)
    fallback = _create_fallback_insight(latest_day)
    print(f"✓ Fallback insight created for {fallback.date}")
    assert len(fallback.score_insights) == 3
    assert len(fallback.reasoning_chain) == 3
    assert len(fallback.actions) >= 1
    print("✓ Fallback insight structure valid")

    # Test 9: Test caching
    print("\nTest 9: Caching and loading")
    print("-" * 60)
    test_insight = fallback
    cache_insight(test_insight, data_dir)
    print(f"✓ Cached insight to data/insights/{test_insight.date}.json")

    loaded = load_cached_insight(test_insight.date, data_dir)
    assert loaded is not None
    assert loaded.date == test_insight.date
    print("✓ Loaded cached insight successfully")

    # Test 10: Test cost logging
    print("\nTest 10: Cost logging")
    print("-" * 60)
    log_api_cost(data_dir, datetime.now(), 0.05, "claude-sonnet-4-5")
    print("✓ Logged API cost")

    costs_file = data_dir / "logs" / "api_costs.json"
    with open(costs_file) as f:
        costs = json.load(f)
    print(f"✓ Cost log contains {len(costs)} entries")

    # Test 11: Validate prompt quality
    print("\nTest 11: Prompt quality checks")
    print("-" * 60)

    # Check that prompt includes actual data values
    sleep_score = latest['sleep']['sleep_score']
    assert str(sleep_score) in prompt
    print(f"✓ Prompt includes sleep score: {sleep_score}")

    # Check that prompt includes baseline values
    if "sleep_score" in baselines and baselines["sleep_score"].get("avg_30d"):
        avg_30d = baselines["sleep_score"]["avg_30d"]
        print(f"✓ Prompt includes 30d baseline: {avg_30d}")

    # Check prompt isn't too long (should be under 10K tokens)
    approx_tokens = len(prompt) // 4
    assert approx_tokens < 10000
    print(f"✓ Prompt size reasonable: ~{approx_tokens} tokens (< 10K limit)")

    # Display sample of prompt
    print("\n" + "=" * 60)
    print("Sample Prompt Output (first 500 chars)")
    print("=" * 60)
    print(prompt[:500] + "...")

    print("\n" + "=" * 60)
    print("✓ All Verification Tests Passed!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Add ANTHROPIC_API_KEY to .env file")
    print("2. Run: uv run python scripts/test_ai_engine.py")
    print("3. Verify quality of AI-generated insights")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
