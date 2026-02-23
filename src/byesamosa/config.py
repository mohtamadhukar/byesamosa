"""Configuration management using pydantic-settings."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import model_validator
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
    oura_email: str = ""
    gmail_otp_email: str = ""
    gmail_otp_app_password: str = ""
    data_dir: Path = Path("data")
    host: str = "127.0.0.1"
    port: int = 8000

    @model_validator(mode="after")
    def _validate_paired_gmail_fields(self) -> "Settings":
        """Ensure Gmail OTP fields are either both set or both empty."""
        has_email = bool(self.gmail_otp_email and self.gmail_otp_email.strip())
        has_password = bool(self.gmail_otp_app_password and self.gmail_otp_app_password.strip())
        if has_email != has_password:
            raise ValueError(
                "GMAIL_OTP_EMAIL and GMAIL_OTP_APP_PASSWORD must both be set or both be empty."
            )
        return self

    @model_validator(mode="after")
    def _validate_oura_email_format(self) -> "Settings":
        """Validate that oura_email looks like an email address when set."""
        if self.oura_email and self.oura_email.strip():
            email = self.oura_email.strip()
            if "@" not in email or "." not in email.split("@")[-1]:
                raise ValueError(
                    f"OURA_EMAIL does not look like a valid email address: {email!r}"
                )
        return self

    @model_validator(mode="after")
    def _validate_data_dir_not_empty(self) -> "Settings":
        """Ensure data_dir is not set to an empty string."""
        if not str(self.data_dir).strip():
            raise ValueError("DATA_DIR must not be empty.")
        return self
