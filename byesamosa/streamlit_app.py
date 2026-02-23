"""ByeSamosa — Oura Ring Dashboard powered by AI insights."""

import json
import time
from datetime import datetime
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from byesamosa.ai.engine import (
    cache_insight,
    generate_insight,
    load_cached_insight,
    log_api_cost,
)
from byesamosa.ai.prompts import format_baselines_for_prompt
from byesamosa.data.models import Baseline
from byesamosa.data.queries import (
    get_deltas,
    get_latest_day,
    get_trends,
    get_workout_recovery_data,
    has_sleep_phases,
)
from byesamosa.data.store import DataStore
from byesamosa.config import Settings

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ByeSamosa",
    page_icon="\U0001fae1",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Data loading (cached per session rerun — data is tiny so fast)
# ---------------------------------------------------------------------------
DATA_DIR = Path("data")


@st.cache_data(ttl=60)
def load_data():
    """Load all dashboard data from disk."""
    store = DataStore(DATA_DIR)
    latest = get_latest_day(store)
    if not latest:
        return None, None, None, None, {}
    deltas = get_deltas(store)
    sleep_trend = get_trends(store, "sleep_score", days=30)
    hrv_trend = get_trends(store, "average_hrv", days=30)
    rhr_trend = get_trends(store, "lowest_heart_rate", days=30)
    insight = load_cached_insight(latest["day"], DATA_DIR)
    workout_recovery = get_workout_recovery_data(store)
    return (
        latest,
        deltas,
        {
            "sleep_score": sleep_trend,
            "average_hrv": hrv_trend,
            "lowest_heart_rate": rhr_trend,
        },
        insight,
        workout_recovery,
    )


data = load_data()
latest, deltas, trends, insight, workout_recovery = data

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
if latest is None:
    st.title("ByeSamosa")
    st.warning(
        "No data found. Import Oura data first: "
        "`python -m byesamosa.pipeline import --raw-dir data/raw/YYYY-MM-DD`"
    )
    st.stop()

st.title("ByeSamosa")
st.caption(f"Data as of **{latest['day']}**")

# ---------------------------------------------------------------------------
# Refresh Insights button (rate-limited to 1 per 60s)
# ---------------------------------------------------------------------------
RATE_LIMIT_SECONDS = 60

col_refresh, col_refresh_status = st.columns([1, 3])
with col_refresh:
    refresh_clicked = st.button("Refresh Insights (~$0.05)")

with col_refresh_status:
    if refresh_clicked:
        last_refresh = st.session_state.get("last_refresh_time", 0)
        elapsed = time.time() - last_refresh
        if elapsed < RATE_LIMIT_SECONDS:
            remaining = int(RATE_LIMIT_SECONDS - elapsed)
            st.warning(f"Rate limited. Try again in {remaining}s.")
        else:
            with st.spinner("Generating AI insight..."):
                try:
                    settings = Settings()
                    store = DataStore(DATA_DIR)
                    _latest = get_latest_day(store)
                    baselines_file = DATA_DIR / "processed" / "baselines.json"
                    _baselines = {}
                    if baselines_file.exists():
                        with open(baselines_file) as f:
                            _baselines = format_baselines_for_prompt(json.load(f))
                    _trends_7d = {
                        m: get_trends(store, m, days=7)
                        for m in ["sleep_score", "readiness_score", "activity_score"]
                    }
                    _has_phases = has_sleep_phases(store)
                    new_insight = generate_insight(
                        _latest, _baselines, _trends_7d, _has_phases, settings
                    )
                    cache_insight(new_insight, DATA_DIR)
                    log_api_cost(DATA_DIR, datetime.now(), 0.05)
                    st.session_state["last_refresh_time"] = time.time()
                    st.success("Insight generated! Reloading...")
                    load_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate insight: {e}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _score_color(score: int | None) -> str:
    """Return a color string based on score value."""
    if score is None:
        return "gray"
    if score >= 85:
        return "#22c55e"  # green
    if score >= 70:
        return "#eab308"  # yellow
    return "#ef4444"  # red


def _make_radar(contributors: list[dict], title: str) -> go.Figure:
    """Create a Plotly Scatterpolar radar chart from contributor data."""
    names = [c["name"] for c in contributors]
    values = [c["value"] for c in contributors]
    # Close the polygon
    names_closed = names + [names[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=names_closed,
            fill="toself",
            fillcolor="rgba(99, 102, 241, 0.15)",
            line=dict(color="#6366f1", width=2),
            marker=dict(size=6),
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=30, b=30),
        height=250,
    )
    return fig


def _render_score_card(
    col, label: str, key: str, score: int | None, delta: float | None
):
    """Render a single score card with metric, radar, and AI one-liner."""
    with col:
        # Score metric
        delta_str = f"{delta:+.0f} vs 30d avg" if delta is not None else None
        st.metric(label=label, value=score if score is not None else "—", delta=delta_str)

        # Radar chart from processed data (source of truth)
        domain_data = latest.get(key, {})
        if domain_data and domain_data.get("contributors"):
            raw_contribs = domain_data["contributors"]
            contribs = [
                {"name": k.replace("_", " ").title(), "value": v}
                for k, v in raw_contribs.items()
                if v is not None
            ]
            if contribs:
                fig = _make_radar(contribs, label)
                st.plotly_chart(fig, use_container_width=True, key=f"radar_{key}")

        # AI one-liner caption (if available)
        if insight and key in insight.score_insights:
            st.caption(insight.score_insights[key].one_liner)

        # Good-looks-like benchmark
        if insight and key in insight.good_looks_like:
            st.caption(f"**Good looks like:** {insight.good_looks_like[key]}")


# ---------------------------------------------------------------------------
# Today View
# ---------------------------------------------------------------------------

# --- Score Cards ---
sleep_data = latest.get("sleep", {})
readiness_data = latest.get("readiness", {})
activity_data = latest.get("activity", {})

col_sleep, col_readiness, col_activity = st.columns(3)

_render_score_card(
    col_sleep,
    "Sleep Score",
    "sleep",
    sleep_data.get("score"),
    deltas.get("sleep_delta"),
)
_render_score_card(
    col_readiness,
    "Readiness Score",
    "readiness",
    readiness_data.get("score") if readiness_data else None,
    deltas.get("readiness_delta"),
)
_render_score_card(
    col_activity,
    "Activity Score",
    "activity",
    activity_data.get("score") if activity_data else None,
    deltas.get("activity_delta"),
)

# --- AI Briefing ---
st.divider()
st.subheader("AI Briefing")

if insight:
    col_reasoning, col_actions = st.columns(2)

    with col_reasoning:
        st.markdown("**Reasoning Chain**")
        for step in insight.reasoning_chain:
            icon = {"Observation": "🔍", "Cause": "🧠", "So what": "⚡"}.get(
                step.label, "•"
            )
            st.markdown(f"{icon} **{step.label}**")
            st.markdown(f"  {step.text}")

    with col_actions:
        st.markdown("**Action Items**")
        for action in insight.actions:
            priority_color = {
                "high": "🔴",
                "medium": "🟡",
                "low": "🟢",
            }.get(action.priority, "⚪")
            st.markdown(
                f"{priority_color} **{action.title}** `{action.tag}`"
            )
            st.caption(action.detail)
else:
    st.info("No AI insight available. Use the Refresh button to generate one.")

# --- Vitals ---
st.divider()
st.subheader("Vitals")

hrv_val = sleep_data.get("average_hrv")
rhr_val = sleep_data.get("lowest_heart_rate")
temp_val = sleep_data.get("temperature_deviation")
breath_val = sleep_data.get("average_breath")

col_hrv, col_rhr, col_temp, col_breath = st.columns(4)

with col_hrv:
    st.metric(label="HRV (avg)", value=f"{hrv_val} ms" if hrv_val else "—")
    if insight and "hrv" in insight.vital_annotations:
        st.caption(insight.vital_annotations["hrv"].text)

with col_rhr:
    st.metric(label="Resting HR", value=f"{rhr_val} bpm" if rhr_val else "—")
    if insight and "rhr" in insight.vital_annotations:
        st.caption(insight.vital_annotations["rhr"].text)

with col_temp:
    if temp_val is not None:
        st.metric(
            label="Body Temp",
            value=f"{temp_val:+.1f} \u00b0C",
        )
    else:
        st.metric(label="Body Temp", value="—")
    if insight and "temp" in insight.vital_annotations:
        st.caption(insight.vital_annotations["temp"].text)

with col_breath:
    st.metric(
        label="Breathing Rate",
        value=f"{breath_val:.1f} /min" if breath_val else "—",
    )
    if insight and "breath" in insight.vital_annotations:
        st.caption(insight.vital_annotations["breath"].text)

# --- Workout & Recovery ---
st.divider()
if workout_recovery and workout_recovery.get("workouts"):
    st.subheader("Workout & Recovery")

    fig_workout = make_subplots(specs=[[{"secondary_y": True}]])

    # Color palette for activity types
    activity_colors = [
        "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899",
        "#14b8a6", "#f97316",
    ]
    activity_types = workout_recovery["activity_types"]
    color_map = {a: activity_colors[i % len(activity_colors)] for i, a in enumerate(activity_types)}

    # Bar traces: one per activity type, stacked
    for activity in activity_types:
        activity_workouts = [w for w in workout_recovery["workouts"] if w["activity"] == activity]
        fig_workout.add_trace(
            go.Bar(
                x=[w["day"] for w in activity_workouts],
                y=[w["calories"] for w in activity_workouts],
                name=activity,
                marker_color=color_map[activity],
            ),
            secondary_y=False,
        )

    # Line trace: continuous readiness across the window
    recovery_readiness = workout_recovery["readiness"]
    if recovery_readiness:
        fig_workout.add_trace(
            go.Scatter(
                x=[r["day"] for r in recovery_readiness],
                y=[r["readiness"] for r in recovery_readiness],
                mode="lines+markers",
                name="Readiness",
                line=dict(color="#22c55e", width=2),
                marker=dict(size=3),
            ),
            secondary_y=True,
        )

    fig_workout.update_layout(
        barmode="stack",
        margin=dict(l=40, r=40, t=30, b=40),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig_workout.update_yaxes(title_text="Calories", secondary_y=False)
    fig_workout.update_yaxes(title_text="Readiness Score", secondary_y=True)
    st.plotly_chart(fig_workout, use_container_width=True, key="workout_recovery")

    st.caption("Readiness shows the full recovery arc — dips after workouts and how many days to recover.")
    if workout_recovery["excluded_count"] > 0:
        st.caption(
            f"{workout_recovery['excluded_count']} workout(s) excluded due to missing calorie data."
        )

# --- Trend Charts ---
st.divider()
st.subheader("Trends (30 days)")

# Load baselines for band overlay
baselines_file = DATA_DIR / "processed" / "baselines.json"
baselines_by_metric: dict[str, list] = {}
if baselines_file.exists():
    with open(baselines_file) as f:
        for b in json.load(f):
            baselines_by_metric.setdefault(b["metric"], []).append(b)

# --- Sleep Score Trend ---
sleep_trend_data = trends.get("sleep_score", [])
if sleep_trend_data:
    days = [d["day"] for d in sleep_trend_data]
    vals = [d["value"] for d in sleep_trend_data]

    fig_sleep = go.Figure()
    fig_sleep.add_trace(
        go.Scatter(
            x=days, y=vals, mode="lines+markers", name="Sleep Score",
            line=dict(color="#6366f1", width=2), marker=dict(size=5),
        )
    )

    # Baseline band (30d avg +/- 1 stddev)
    sleep_baselines = baselines_by_metric.get("sleep_score", [])
    if sleep_baselines:
        bl_days = [b["day"] for b in sleep_baselines if b.get("avg_30d")]
        bl_avg = [b["avg_30d"] for b in sleep_baselines if b.get("avg_30d")]
        bl_upper = [
            b["avg_30d"] + (b.get("std_30d") or 0)
            for b in sleep_baselines if b.get("avg_30d")
        ]
        bl_lower = [
            b["avg_30d"] - (b.get("std_30d") or 0)
            for b in sleep_baselines if b.get("avg_30d")
        ]
        fig_sleep.add_trace(
            go.Scatter(
                x=bl_days, y=bl_upper, mode="lines",
                line=dict(width=0), showlegend=False,
            )
        )
        fig_sleep.add_trace(
            go.Scatter(
                x=bl_days, y=bl_lower, mode="lines",
                fill="tonexty", fillcolor="rgba(99,102,241,0.08)",
                line=dict(width=0), name="30d avg \u00b1 1\u03c3",
            )
        )

    fig_sleep.update_layout(
        title="Sleep Score",
        yaxis=dict(range=[40, 100]),
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_sleep, use_container_width=True, key="trend_sleep")
    if insight and "sleep_score" in insight.trend_annotations:
        ta = insight.trend_annotations["sleep_score"]
        st.caption(f"{'📈' if ta.icon == 'up' else '📉' if ta.icon == 'down' else '❤️'} {ta.text}")

# --- HRV + RHR Dual-Axis Trend ---
hrv_trend_data = trends.get("average_hrv", [])
rhr_trend_data = trends.get("lowest_heart_rate", [])
if hrv_trend_data or rhr_trend_data:
    fig_dual = make_subplots(specs=[[{"secondary_y": True}]])

    if hrv_trend_data:
        fig_dual.add_trace(
            go.Scatter(
                x=[d["day"] for d in hrv_trend_data],
                y=[d["value"] for d in hrv_trend_data],
                mode="lines+markers", name="HRV (ms)",
                line=dict(color="#22c55e", width=2), marker=dict(size=4),
            ),
            secondary_y=False,
        )

    if rhr_trend_data:
        fig_dual.add_trace(
            go.Scatter(
                x=[d["day"] for d in rhr_trend_data],
                y=[d["value"] for d in rhr_trend_data],
                mode="lines+markers", name="RHR (bpm)",
                line=dict(color="#ef4444", width=2), marker=dict(size=4),
            ),
            secondary_y=True,
        )

    fig_dual.update_layout(
        title="HRV + Resting Heart Rate",
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig_dual.update_yaxes(title_text="HRV (ms)", secondary_y=False)
    fig_dual.update_yaxes(title_text="RHR (bpm)", secondary_y=True)
    st.plotly_chart(fig_dual, use_container_width=True, key="trend_hrv_rhr")
    if insight and "hrv_rhr" in insight.trend_annotations:
        ta = insight.trend_annotations["hrv_rhr"]
        st.caption(f"{'📈' if ta.icon == 'up' else '📉' if ta.icon == 'down' else '❤️'} {ta.text}")
