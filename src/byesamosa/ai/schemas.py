"""Pydantic models for AI-generated insights.

These models define the structured output format for Claude API responses.
All insights are cached to data/insights/YYYY-MM-DD.json.
"""

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel


class ContributorLabel(BaseModel):
    """Label for a single contributor to a score.

    Used in radar charts to show which factors are helping/hurting a score.
    """
    name: str  # e.g. "Latency", "REM Sleep", "HRV Balance"
    value: int  # 0-100 score for this contributor
    tag: Literal["boost", "ok", "drag"]  # boost: >=85, ok: 75-84, drag: <75


class ScoreInsight(BaseModel):
    """AI one-liner insight for a single score card (Sleep/Readiness/Activity).

    Example: "Deep sleep was your best in 2 weeks, but high latency dragged the score."
    """
    one_liner: str  # Concise summary of what drove the score
    contributors: list[ContributorLabel]  # Sorted best→worst by value


class ReasoningStep(BaseModel):
    """Single step in a reasoning chain.

    Chains follow the pattern: Observation → Cause → So what
    """
    label: str  # "Observation" | "Cause" | "So what"
    text: str  # The reasoning content for this step


class ActionItem(BaseModel):
    """Actionable recommendation for the user.

    Example:
    - title: "Go hard if you have a workout planned"
    - detail: "Readiness 90 + HRV rebound = full capacity..."
    - priority: "high"
    - tag: "Optimize performance"
    """
    title: str  # Short imperative statement
    detail: str  # Explanation of why/how
    priority: Literal["high", "medium", "low"]
    tag: str  # Category label, e.g. "Fix REM", "Break trend", "Optional"


class ChartAnnotation(BaseModel):
    """AI callout text for a chart or vital card.

    Example: "Best in 10 days. Strong parasympathetic rebound..."
    """
    text: str


class TrendAnnotation(BaseModel):
    """AI annotation for a trend chart with an icon indicator."""
    icon: str  # "up" | "down" | "heart" - indicates trend direction or quality
    text: str  # Explanation of the trend


class AIInsight(BaseModel):
    """Complete AI-generated insight for a single day.

    Cached to data/insights/YYYY-MM-DD.json after generation.
    """
    date: date

    # One-liner insights for each score type
    score_insights: dict[str, ScoreInsight]  # keys: "sleep", "readiness", "activity"

    # Reasoning chain (3 steps: observation → cause → so what)
    reasoning_chain: list[ReasoningStep]

    # Prioritized action items (3-4 items)
    actions: list[ActionItem]

    # Chart annotations (conditional - only if sleep phase data available)
    hypnogram_annotation: Optional[ChartAnnotation] = None

    # Vital card context sentences
    vital_annotations: dict[str, ChartAnnotation]  # keys: "hrv", "rhr", "temp", "breath"

    # Trend chart annotations
    trend_annotations: dict[str, TrendAnnotation]  # keys: "sleep_score", "hrv_rhr"

    # Personalized benchmark descriptions
    good_looks_like: dict[str, str]  # keys: "sleep", "readiness", "activity"
