from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent
ROOT_ENV = ROOT_DIR / ".env"

load_dotenv(ROOT_ENV, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "RAGLab AI"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/raglab.db"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    upload_max_bytes: int = 10 * 1024 * 1024
    chunk_size: int = 900
    chunk_overlap: int = 150
    embedding_dimensions: int = 384

    grok_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("GROK_API_KEY", "XAI_API_KEY")
    )
    grok_model: str = Field(default="latest", validation_alias=AliasChoices("GROK_MODEL", "XAI_MODEL"))
    xai_base_url: str = "https://api.x.ai/v1"
    provider_timeout_seconds: float = 20.0
    provider_max_retries: int = 1

    x_bearer_token: SecretStr | None = None
    x_api_key: SecretStr | None = None
    x_api_secret: SecretStr | None = None
    x_access_token: SecretStr | None = None
    x_access_token_secret: SecretStr | None = None

    langsmith_tracing: bool = False
    langsmith_api_key: SecretStr | None = None
    langsmith_project: str = "raglab-ai-local"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def sqlite_path(self) -> Path | None:
        if self.database_url.startswith("sqlite:///"):
            raw_path = self.database_url.removeprefix("sqlite:///")
            path = Path(raw_path)
            if not path.is_absolute():
                path = BACKEND_DIR / path
            return path
        return None

    @property
    def is_grok_configured(self) -> bool:
        return self.grok_api_key is not None and bool(self.grok_api_key.get_secret_value())

    @property
    def configured_secret_names(self) -> list[str]:
        names: list[str] = []
        if self.is_grok_configured:
            names.append("GROK_API_KEY")
        if self.x_bearer_token:
            names.append("X_BEARER_TOKEN")
        if self.x_api_key:
            names.append("X_API_KEY")
        if self.langsmith_api_key:
            names.append("LANGSMITH_API_KEY")
        return names


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    sqlite_path = settings.sqlite_path
    if sqlite_path:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    (BACKEND_DIR / "data" / "uploads").mkdir(parents=True, exist_ok=True)
    return settings

