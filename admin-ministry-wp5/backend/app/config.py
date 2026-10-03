from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# One .env for the whole module, at admin-ministry-wp5/.env
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_env: str = "dev"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://mahara:mahara@localhost:5432/mahara_match"
    cors_origins: str = "http://localhost:5174"

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()