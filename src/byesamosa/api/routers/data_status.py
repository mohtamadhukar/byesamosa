import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from byesamosa.api.deps import get_store
from byesamosa.data.store import DataStore

router = APIRouter()


class RawExport(BaseModel):
    date: str
    file_count: int


class ProcessedRange(BaseModel):
    earliest: str
    latest: str


class DataStatusResponse(BaseModel):
    raw_exports: list[RawExport]
    processed_range: ProcessedRange | None


def _scan_raw_exports(raw_dir: Path) -> list[RawExport]:
    """Find date-named directories under data/raw/ and count CSVs in each."""
    if not raw_dir.exists():
        return []
    date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    exports = []
    for entry in sorted(raw_dir.iterdir(), reverse=True):
        if entry.is_dir() and date_pattern.match(entry.name):
            csv_count = len(list(entry.glob("*.csv")))
            if csv_count > 0:
                exports.append(RawExport(date=entry.name, file_count=csv_count))
    return exports


def _get_processed_range(processed_dir: Path) -> ProcessedRange | None:
    """Find earliest and latest dates across all processed JSON files."""
    all_days: list[str] = []
    for json_file in processed_dir.glob("daily_*.json"):
        try:
            data = json.loads(json_file.read_text())
            for record in data:
                if "day" in record:
                    all_days.append(record["day"])
        except (json.JSONDecodeError, KeyError):
            continue
    if not all_days:
        return None
    all_days.sort()
    return ProcessedRange(earliest=all_days[0], latest=all_days[-1])


@router.get("/data/status")
def data_status(store: DataStore = Depends(get_store)) -> DataStatusResponse:
    raw_dir = store.data_dir / "raw"
    return DataStatusResponse(
        raw_exports=_scan_raw_exports(raw_dir),
        processed_range=_get_processed_range(store.processed_dir),
    )
