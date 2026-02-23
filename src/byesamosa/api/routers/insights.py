import json
import time

from fastapi import APIRouter, Depends, HTTPException

from byesamosa.ai.engine import cache_insight, generate_insight
from byesamosa.ai.prompts import format_baselines_for_prompt
from byesamosa.api.deps import get_settings, get_store
from byesamosa.config import Settings
from byesamosa.data.queries import get_latest_day, get_trends, has_sleep_phases
from byesamosa.data.store import DataStore

router = APIRouter()

_last_refresh: float = 0.0


@router.post("/insights/refresh")
def refresh_insight(
    store: DataStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    global _last_refresh

    now = time.monotonic()
    if now - _last_refresh < 60:
        raise HTTPException(status_code=429, detail="Rate limited. Try again in 60 seconds.")

    latest = get_latest_day(store)
    if not latest:
        raise HTTPException(status_code=404, detail="No data found")

    target_date = latest["day"]

    # Load baselines
    baselines_file = store.processed_dir / "baselines.json"
    baselines_prompt: dict = {}
    if baselines_file.exists():
        with open(baselines_file) as f:
            baselines_list = json.load(f)
        baselines_prompt = format_baselines_for_prompt(baselines_list)

    # Get 7-day trends
    trends_7d = {
        "sleep_score": get_trends(store, "sleep_score", 7),
        "readiness_score": get_trends(store, "readiness_score", 7),
        "activity_score": get_trends(store, "activity_score", 7),
    }

    sleep_phases = has_sleep_phases(store)

    insight = generate_insight(latest, baselines_prompt, trends_7d, sleep_phases, settings)
    cache_insight(insight, settings.data_dir)

    _last_refresh = time.monotonic()

    return insight.model_dump(mode="json")
