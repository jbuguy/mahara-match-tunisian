from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "mahara-match"
    app_version: str = "0.1.0"
    environment: str = "development"
    app_env: str = "development"
    database_url: str | None = None
    jwt_secret: str = "mahara-match-super-secret-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    google_client_id: str | None = None
    google_client_secret: str | None = None
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    llm_base_url: str = "http://localhost:1234/v1"
    llm_model: str = "local-model"
    llm_embedding_model: str = "multilingual-e5-base"
    llm_api_key: str | None = None
    llm_timeout_seconds: float = 60.0
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    ministry_market_feed_url: str | None = None
    ministry_market_feed_token: str | None = None
    ministry_market_worker_poll_seconds: float = 3.0
    ministry_market_feed_timeout_seconds: float = 30.0
    s3_endpoint_url: str | None = None
    s3_region: str = "eu-central-1"
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_starttls: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
