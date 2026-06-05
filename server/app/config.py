from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    log_level: str = "INFO"
    metrics_enabled: bool = True
    # Comma-separated list of allowed CORS origins. "*" allows all (dev only).
    allowed_origins: str = "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173"

    halyk_sso_issuer: str = "https://sso.halykbank.kz/realms/homebank"
    halyk_sso_client_id: str = "resale-web"

    google_maps_api_key: str = ""

    krisha_base_url: str = "https://krisha.kz"
    krisha_scrape_mode: str = "mock"

    cbs_base_url: str = "https://cbs.halykbank.kz/api/v1"
    cbs_api_key: str = ""
    cbs_mode: str = "mock"

    genai_base_url: str = "https://api.openai.com/v1"
    genai_api_key: str = ""
    genai_model: str = "gpt-4o-mini"
    genai_mode: str = "mock"


settings = Settings()
