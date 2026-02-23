import json
from typing import Optional

from fastapi import APIRouter, Depends, Query

from byesamosa.api.deps import get_store
from byesamosa.data.store import DataStore

router = APIRouter()


@router.get("/baselines")
def baselines(
    metric: Optional[str] = Query(default=None),
    store: DataStore = Depends(get_store),
):
    baselines_file = store.processed_dir / "baselines.json"
    if not baselines_file.exists():
        return []

    with open(baselines_file) as f:
        data = json.load(f)

    if metric:
        data = [b for b in data if b.get("metric") == metric]

    return data
