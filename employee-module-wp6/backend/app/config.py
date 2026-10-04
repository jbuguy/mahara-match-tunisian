from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# employee-module-wp6/.env, shared with the frontend (which only reads VITE_* names).
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    database_url: str | None = None
    supabase_url: str | None = None
    cors_origins: str = "http://localhost:5173"
    app_env: str = "development"
    # Profile assistant (Groq free plan). Read only here, on the backend: never sent to the browser.
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
