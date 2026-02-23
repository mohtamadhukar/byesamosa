from functools import lru_cache
from pathlib import Path

from byesamosa.config import Settings
from byesamosa.data.store import DataStore


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_store() -> DataStore:
    settings = get_settings()
    return DataStore(settings.data_dir)
