"""Test AI engine and prompt generation."""

import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from byesamosa.ai.schemas import AIInsight, ScoreInsight, ContributorLabel, ReasoningStep, ActionItem, ChartAnnotation, TrendAnnotation
from byesamosa.data.models import DailyActivity, DailyReadiness, DailySleep
from byesamosa.data.store import DataStore


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "raw").mkdir(exist_ok=True)
        (tmpdir_path / "processed").mkdir(exist_ok=True)
        (tmpdir_path / "insights").mkdir(exist_ok=True)
        (tmpdir_path / "logs").mkdir(exist_ok=True)
        yield tmpdir_path


@pytest.fixture
def sample_store(temp_data_dir):
    """Create a sample data store with test data."""
    store = DataStore(temp_data_dir)
    
    base_date = date(2025, 1, 1)
    sleep_records = []
    readiness_records = []
    activity_records = []
    
    for i in range(10):
        current_date = base_date + timedelta(days=i)
        
        sleep = DailySleep(
            day=current_date,
            sleep_score=75 + i,
            total_sleep_seconds=28800 + (i * 600),
            rem_sleep_seconds=7200,
            deep_sleep_seconds=9600,
            efficiency=0.85,
            average_hrv=50 + i,
            lowest_heart_rate=50,
        )
        sleep_records.append(sleep)
        
        readiness = DailyReadiness(
            day=current_date,
            readiness_score=70 + i,
        )
        readiness_records.append(readiness)
        
        activity = DailyActivity(
            day=current_date,
            activity_score=65 + i,
            steps=8000 + (i * 100),
            active_calories=400,
        )
        activity_records.append(activity)
    
    store.upsert_sleep(sleep_records)
    store.upsert_readiness(readiness_records)
    store.upsert_activity(activity_records)
    
    return store


def test_ai_insight_schema_valid():
    """Test that AIInsight schema can be created with valid data."""
    contributor = ContributorLabel(name="Deep Sleep", value=85, tag="boost")
    score_insight = ScoreInsight(one_liner="Deep sleep was excellent", contributors=[contributor])
    reasoning_step = ReasoningStep(label="Observation", text="Your sleep was good")
    action_item = ActionItem(title="Keep it up", detail="Your sleep is great", priority="high", tag="Consistency")
    chart_annotation = ChartAnnotation(text="Best in 10 days")
    trend_annotation = TrendAnnotation(icon="up", text="Trending upward")
    
    insight = AIInsight(
        date=date(2025, 1, 1),
        score_insights={
            "sleep": score_insight,
            "readiness": score_insight,
            "activity": score_insight,
        },
        reasoning_chain=[reasoning_step, reasoning_step, reasoning_step],
        actions=[action_item],
        vital_annotations={
            "hrv": chart_annotation,
            "rhr": chart_annotation,
            "temp": chart_annotation,
            "breath": chart_annotation,
        },
        trend_annotations={
            "sleep_score": trend_annotation,
            "hrv_rhr": trend_annotation,
        },
        good_looks_like={
            "sleep": "Well-rested",
            "readiness": "Ready to go",
            "activity": "Active",
        },
    )
    
    assert insight.date == date(2025, 1, 1)
    assert len(insight.reasoning_chain) == 3
    assert len(insight.actions) == 1


def test_contributor_label():
    """Test ContributorLabel creation."""
    contributor = ContributorLabel(name="Deep Sleep", value=90, tag="boost")
    assert contributor.name == "Deep Sleep"
    assert contributor.value == 90
    assert contributor.tag == "boost"


def test_score_insight_structure():
    """Test ScoreInsight structure."""
    contributor = ContributorLabel(name="REM Sleep", value=75, tag="ok")
    insight = ScoreInsight(one_liner="REM sleep was adequate", contributors=[contributor])
    assert insight.one_liner == "REM sleep was adequate"
    assert len(insight.contributors) == 1


def test_reasoning_step():
    """Test ReasoningStep creation."""
    step = ReasoningStep(label="Observation", text="Sleep was 8 hours")
    assert step.label == "Observation"
    assert step.text == "Sleep was 8 hours"


def test_action_item():
    """Test ActionItem creation."""
    action = ActionItem(
        title="Increase exercise",
        detail="Your activity is low",
        priority="high",
        tag="Activity"
    )
    assert action.title == "Increase exercise"
    assert action.priority == "high"


def test_chart_annotation():
    """Test ChartAnnotation creation."""
    annotation = ChartAnnotation(text="Best day in 2 weeks")
    assert annotation.text == "Best day in 2 weeks"


def test_trend_annotation():
    """Test TrendAnnotation creation."""
    annotation = TrendAnnotation(icon="up", text="Improving trend")
    assert annotation.icon == "up"
    assert annotation.text == "Improving trend"


def test_ai_insight_json_serialization():
    """Test that AIInsight can be serialized and deserialized."""
    contributor = ContributorLabel(name="Deep Sleep", value=85, tag="boost")
    score_insight = ScoreInsight(one_liner="Great sleep", contributors=[contributor])
    reasoning_step = ReasoningStep(label="Observation", text="Excellent")
    action_item = ActionItem(title="Continue", detail="Keep going", priority="high", tag="Consistency")
    chart_annotation = ChartAnnotation(text="Good")
    trend_annotation = TrendAnnotation(icon="up", text="Up")
    
    original = AIInsight(
        date=date(2025, 1, 1),
        score_insights={
            "sleep": score_insight,
            "readiness": score_insight,
            "activity": score_insight,
        },
        reasoning_chain=[reasoning_step, reasoning_step, reasoning_step],
        actions=[action_item],
        vital_annotations={
            "hrv": chart_annotation,
            "rhr": chart_annotation,
            "temp": chart_annotation,
            "breath": chart_annotation,
        },
        trend_annotations={
            "sleep_score": trend_annotation,
            "hrv_rhr": trend_annotation,
        },
        good_looks_like={
            "sleep": "Rested",
            "readiness": "Ready",
            "activity": "Active",
        },
    )
    
    json_str = original.model_dump_json()
    restored = AIInsight.model_validate_json(json_str)
    
    assert restored.date == original.date
    assert len(restored.reasoning_chain) == 3


def test_ai_insight_with_hypnogram():
    """Test AIInsight with optional hypnogram annotation."""
    contributor = ContributorLabel(name="Sleep", value=85, tag="boost")
    score_insight = ScoreInsight(one_liner="Good", contributors=[contributor])
    reasoning_step = ReasoningStep(label="Observation", text="Good")
    action_item = ActionItem(title="Continue", detail="Good", priority="high", tag="Tag")
    annotation = ChartAnnotation(text="Good")
    trend_annotation = TrendAnnotation(icon="up", text="Up")
    
    insight = AIInsight(
        date=date(2025, 1, 1),
        score_insights={
            "sleep": score_insight,
            "readiness": score_insight,
            "activity": score_insight,
        },
        reasoning_chain=[reasoning_step] * 3,
        actions=[action_item],
        hypnogram_annotation=annotation,
        vital_annotations={
            "hrv": annotation,
            "rhr": annotation,
            "temp": annotation,
            "breath": annotation,
        },
        trend_annotations={
            "sleep_score": trend_annotation,
            "hrv_rhr": trend_annotation,
        },
        good_looks_like={
            "sleep": "Rested",
            "readiness": "Ready",
            "activity": "Active",
        },
    )
    
    assert insight.hypnogram_annotation is not None
    assert insight.hypnogram_annotation.text == "Good"
