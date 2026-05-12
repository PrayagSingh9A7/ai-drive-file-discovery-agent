from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Google Drive File Discovery Assistant"
    app_env: Literal["local", "production", "test"] = "local"

    llm_provider: Literal["gemini", "openai", "groq"] = "gemini"
    gemini_api_key: str | None = None
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    openai_model: str = "gpt-4o-mini"
    groq_model: str = "llama-3.1-70b-versatile"

    google_application_credentials: str = Field(default="", alias="GOOGLE_APPLICATION_CREDENTIALS")
    google_drive_folder_id: str = Field(default="", alias="GOOGLE_DRIVE_FOLDER_ID")

    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"
    drive_page_size: int = 10
    drive_max_pages: int = 5
    request_timeout_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("cors_origins")
    @classmethod
    def normalize_cors_origins(cls, value: str) -> str:
        return ",".join(origin.strip() for origin in value.split(",") if origin.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
