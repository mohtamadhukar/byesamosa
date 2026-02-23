"""Configuration management using pydantic-settings."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


# Find project root and load .env explicitly
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
_env_file = _project_root / ".env"

if _env_file.exists():
    load_dotenv(_env_file)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(extra="ignore")

    anthropic_api_key: str = "placeholder"  # Will be loaded from .env
    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = 8000
