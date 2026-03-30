import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _get_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


def _get_float(name: str, default: float) -> float:
    value = _get_env(name)
    if not value:
        return default
    return float(value)


def _get_int(name: str, default: int) -> int:
    value = _get_env(name)
    if not value:
        return default
    return int(value)


def _get_bool(name: str, default: bool) -> bool:
    value = _get_env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _get_list(name: str, default: list[str]) -> list[str]:
    value = _get_env(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = _get_env("APP_NAME", "AI Studio Backend")
    app_env: str = _get_env("APP_ENV", "development")
    app_host: str = _get_env("APP_HOST", "127.0.0.1")
    app_port: int = _get_int("APP_PORT", 8000)
    api_prefix: str = _get_env("API_PREFIX", "/api/v1")
    log_level: str = _get_env("LOG_LEVEL", "INFO").upper()
    database_url: str = _get_env("DATABASE_URL", "sqlite:///./ai_studio.db")
    cors_origins: list[str] = None
    groq_api_key: str = _get_env("GROQ_API_KEY")
    openrouter_api_key: str = _get_env("OPENROUTER_API_KEY")
    groq_model: str = _get_env("GROQ_MODEL", "llama-3.3-70b-versatile")
    openrouter_model: str = _get_env("OPENROUTER_MODEL", "google/gemma-3n-e4b-it:free")
    request_timeout: float = _get_float("AI_REQUEST_TIMEOUT", 30.0)
    request_retries: int = _get_int("AI_REQUEST_RETRIES", 3)
    retry_delay_seconds: float = _get_float("AI_RETRY_DELAY_SECONDS", 1.5)
    enable_docs: bool = _get_bool("ENABLE_DOCS", True)
    service_api_key: str = _get_env("SERVICE_API_KEY")

    def __post_init__(self):
        default_origins = [
            "http://localhost:8069",
            "http://127.0.0.1:8069",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        object.__setattr__(self, "cors_origins", _get_list("CORS_ORIGINS", default_origins))

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()
