from fastapi import APIRouter, Depends, HTTPException

from byesamosa.ai.engine import load_cached_insight
from byesamosa.api.deps import get_settings, get_store
from byesamosa.config import Settings
from byesamosa.data.queries import get_deltas, get_latest_day
from byesamosa.data.store import DataStore

router = APIRouter()


@router.get("/dashboard")
def dashboard(
    store: DataStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
):
    latest = get_latest_day(store)
    if not latest:
        raise HTTPException(status_code=404, detail="No data found")

    target_date = latest["day"]
    deltas = get_deltas(store, target_date)
    insight = load_cached_insight(target_date, settings.data_dir)

    return {
        "latest": latest,
        "deltas": deltas,
        "insight": insight.model_dump(mode="json") if insight else None,
    }
