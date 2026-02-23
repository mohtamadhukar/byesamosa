from fastapi import APIRouter, Depends, Query

from byesamosa.api.deps import get_store
from byesamosa.data.queries import get_workout_recovery_data
from byesamosa.data.store import DataStore

router = APIRouter()


@router.get("/workouts")
def workouts(
    days: int = Query(default=30, ge=1, le=365),
    store: DataStore = Depends(get_store),
):
    return get_workout_recovery_data(store, days)
