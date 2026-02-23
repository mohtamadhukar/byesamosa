from fastapi import APIRouter, Depends, Query

from byesamosa.api.deps import get_store
from byesamosa.data.queries import get_trends
from byesamosa.data.store import DataStore

router = APIRouter()


@router.get("/trends")
def trends(
    days: int = Query(default=30, ge=1, le=365),
    store: DataStore = Depends(get_store),
):
    return {
        "sleep_score": get_trends(store, "sleep_score", days),
        "average_hrv": get_trends(store, "average_hrv", days),
        "lowest_heart_rate": get_trends(store, "lowest_heart_rate", days),
    }
