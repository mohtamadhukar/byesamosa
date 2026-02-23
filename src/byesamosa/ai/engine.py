"""AI engine for generating personalized insights using Claude API.

Handles API calls, response validation, caching, and cost tracking.
"""

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import anthropic
from pydantic import ValidationError

from byesamosa.ai.prompts import SYSTEM_PROMPT, build_user_prompt, format_baselines_for_prompt
from byesamosa.ai.schemas import AIInsight
from byesamosa.config import Settings

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> str:
    """Extract JSON from text that may be wrapped in markdown code fences."""
    # Try to find JSON inside ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def generate_insight(
    latest: dict,
    baselines: dict,
    trends_7d: dict,
    has_sleep_phases: bool,
    settings: Settings,
) -> AIInsight:
    """Generate AI insight for the latest day using Claude API.

    Args:
        latest: Latest day's data from get_latest_day()
        baselines: Baseline statistics for all metrics
        trends_7d: Last 7 days of score trends
        has_sleep_phases: Whether sleep phase interval data is available
        settings: Application settings (API key, etc.)

    Returns:
        AIInsight object with reasoning, actions, and annotations

    Raises:
        ValueError: If API call fails or response validation fails after retry
    """
    # Build prompt
    user_prompt = build_user_prompt(latest, baselines, trends_7d, has_sleep_phases)

    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Cost protection: max_tokens=4096 caps cost at ~$0.05 per call
    max_tokens = 4096

    try:
        # First attempt
        logger.info(f"Generating insight for {latest.get('day')} with Claude API...")
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
        )

        # Extract text content
        response_text = ""
        for block in response.content:
            if block.type == "text":
                response_text += block.text

        # Parse JSON response (strip markdown code fences if present)
        try:
            insight_data = json.loads(_extract_json(response_text))
            insight_data["date"] = latest.get("day")
            insight = AIInsight.model_validate(insight_data)
            logger.info("Successfully generated and validated insight")
            return insight

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"First attempt validation failed: {e}")

            # Retry with error feedback
            logger.info("Retrying with error feedback...")
            retry_prompt = f"{user_prompt}\n\n---\n\nPrevious attempt failed with error:\n{str(e)}\n\nPlease fix the JSON and try again. Return ONLY valid JSON matching the AIInsight schema."

            retry_response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": retry_prompt,
                    }
                ],
            )

            # Extract retry response
            retry_text = ""
            for block in retry_response.content:
                if block.type == "text":
                    retry_text += block.text

            # Parse retry response (strip markdown code fences if present)
            retry_data = json.loads(_extract_json(retry_text))
            retry_data["date"] = latest.get("day")
            insight = AIInsight.model_validate(retry_data)
            logger.info("Successfully generated insight on retry")
            return insight

    except Exception as e:
        logger.error(f"Failed to generate insight: {e}")
        # Return fallback insight
        logger.warning("Returning fallback insight due to API error")
        return _create_fallback_insight(latest.get("day"))


def _create_fallback_insight(day: date) -> AIInsight:
    """Create a minimal fallback insight when API fails.

    Args:
        day: Date for the insight

    Returns:
        Basic AIInsight with placeholder content
    """
    from byesamosa.ai.schemas import (
        ActionItem,
        ChartAnnotation,
        ContributorLabel,
        ReasoningStep,
        ScoreInsight,
        TrendAnnotation,
    )

    return AIInsight(
        date=day,
        score_insights={
            "sleep": ScoreInsight(
                one_liner="Unable to generate insight - API error occurred.",
                contributors=[
                    ContributorLabel(name="Total Sleep", value=50, tag="drag"),
                    ContributorLabel(name="Rem Sleep", value=50, tag="drag"),
                    ContributorLabel(name="Deep Sleep", value=50, tag="drag"),
                    ContributorLabel(name="Efficiency", value=50, tag="drag"),
                    ContributorLabel(name="Latency", value=50, tag="drag"),
                    ContributorLabel(name="Restfulness", value=50, tag="drag"),
                    ContributorLabel(name="Timing", value=50, tag="drag"),
                ],
            ),
            "readiness": ScoreInsight(
                one_liner="Unable to generate insight - API error occurred.",
                contributors=[
                    ContributorLabel(name="Hrv Balance", value=50, tag="drag"),
                    ContributorLabel(name="Resting Heart Rate", value=50, tag="drag"),
                    ContributorLabel(name="Recovery Index", value=50, tag="drag"),
                    ContributorLabel(name="Sleep Balance", value=50, tag="drag"),
                    ContributorLabel(name="Body Temperature", value=50, tag="drag"),
                    ContributorLabel(name="Activity Balance", value=50, tag="drag"),
                ],
            ),
            "activity": ScoreInsight(
                one_liner="Unable to generate insight - API error occurred.",
                contributors=[
                    ContributorLabel(name="Meet Daily Targets", value=50, tag="drag"),
                    ContributorLabel(name="Move Every Hour", value=50, tag="drag"),
                    ContributorLabel(name="Stay Active", value=50, tag="drag"),
                    ContributorLabel(name="Training Frequency", value=50, tag="drag"),
                ],
            ),
        },
        reasoning_chain=[
            ReasoningStep(
                label="Observation",
                text="API error prevented insight generation.",
            ),
            ReasoningStep(
                label="Cause",
                text="Claude API request failed or validation error occurred.",
            ),
            ReasoningStep(
                label="So what",
                text="Try regenerating the insight or check API key configuration.",
            ),
        ],
        actions=[
            ActionItem(
                title="Regenerate insight",
                detail="Click the refresh button to try generating insights again.",
                priority="high",
                tag="Fix issue",
            ),
        ],
        vital_annotations={
            "hrv": ChartAnnotation(text="Unable to analyze - API error"),
            "rhr": ChartAnnotation(text="Unable to analyze - API error"),
            "temp": ChartAnnotation(text="Unable to analyze - API error"),
            "breath": ChartAnnotation(text="Unable to analyze - API error"),
        },
        trend_annotations={
            "sleep_score": TrendAnnotation(
                icon="heart",
                text="Unable to analyze - API error",
            ),
            "hrv_rhr": TrendAnnotation(
                icon="heart",
                text="Unable to analyze - API error",
            ),
        },
        good_looks_like={
            "sleep": "Unable to generate benchmark - API error",
            "readiness": "Unable to generate benchmark - API error",
            "activity": "Unable to generate benchmark - API error",
        },
    )


def cache_insight(insight: AIInsight, data_dir: Path) -> None:
    """Save insight to data/insights/YYYY-MM-DD.json.

    Args:
        insight: AIInsight object to cache
        data_dir: Path to data directory
    """
    insights_dir = data_dir / "insights"
    insights_dir.mkdir(parents=True, exist_ok=True)

    insight_file = insights_dir / f"{insight.date}.json"
    with open(insight_file, "w") as f:
        json.dump(insight.model_dump(mode="json"), f, indent=2, default=str)

    logger.info(f"Cached insight to {insight_file}")


def load_cached_insight(target_date: date, data_dir: Path) -> Optional[AIInsight]:
    """Load cached insight from data/insights/YYYY-MM-DD.json.

    Args:
        target_date: Date to load insight for
        data_dir: Path to data directory

    Returns:
        AIInsight if found, None otherwise
    """
    insight_file = data_dir / "insights" / f"{target_date}.json"

    if not insight_file.exists():
        return None

    try:
        with open(insight_file) as f:
            data = json.load(f)
            return AIInsight.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Failed to load cached insight from {insight_file}: {e}")
        return None


def log_api_cost(
    data_dir: Path,
    timestamp: datetime,
    estimated_cost: float,
    model: str = "claude-sonnet-4-5",
) -> None:
    """Log API call cost to data/logs/api_costs.json.

    Args:
        data_dir: Path to data directory
        timestamp: Timestamp of API call
        estimated_cost: Estimated cost in USD
        model: Model name used
    """
    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    costs_file = logs_dir / "api_costs.json"

    # Load existing logs
    if costs_file.exists():
        with open(costs_file) as f:
            costs = json.load(f)
    else:
        costs = []

    # Append new log entry
    costs.append(
        {
            "timestamp": timestamp.isoformat(),
            "model": model,
            "estimated_cost_usd": estimated_cost,
        }
    )

    # Save updated logs
    with open(costs_file, "w") as f:
        json.dump(costs, f, indent=2)

    logger.info(f"Logged API cost: ${estimated_cost:.4f}")


def estimate_cost(input_tokens: int, output_tokens: int, model: str = "claude-sonnet-4-5") -> float:
    """Estimate API call cost based on token counts.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name

    Returns:
        Estimated cost in USD

    Note:
        Pricing as of Feb 2025 (Claude Sonnet 4.5):
        - Input: $3 per 1M tokens
        - Output: $15 per 1M tokens
    """
    # Pricing per 1M tokens (as of Feb 2025)
    if "sonnet-4" in model or "sonnet-4-5" in model:
        input_price = 3.0
        output_price = 15.0
    else:
        # Default fallback pricing
        input_price = 3.0
        output_price = 15.0

    input_cost = (input_tokens / 1_000_000) * input_price
    output_cost = (output_tokens / 1_000_000) * output_price

    return input_cost + output_cost
