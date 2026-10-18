"""Application settings loaded from environment variables (and the optional .env file)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration. Every field maps to an upper-case environment variable."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_ignore_empty=True,
    )

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    model_root: str = Field(default="gemini-3.1-flash-lite", alias="AURORA_MODEL_ROOT")
    model_specialist: str = Field(default="gemini-2.5-flash", alias="AURORA_MODEL_SPECIALIST")
    # Optional per-specialist overrides (default: AURORA_MODEL_SPECIALIST). Spreading agents
    # over different models also spreads the per-model quotas of free-tier keys.
    model_reservas: str = Field(default="", alias="AURORA_MODEL_RESERVAS")
    model_visitantes: str = Field(default="", alias="AURORA_MODEL_VISITANTES")
    model_regulamento: str = Field(default="", alias="AURORA_MODEL_REGULAMENTO")

    dados_dir: Path = Field(default=PROJECT_ROOT / "dados", alias="AURORA_DADOS_DIR")
    db_path: Path = Field(default=PROJECT_ROOT / "var" / "aurora.db", alias="AURORA_DB_PATH")
    sessions_db_url: str = Field(default="", alias="AURORA_SESSIONS_DB_URL")

    enable_docs: bool = Field(default=True, alias="AURORA_ENABLE_DOCS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    @property
    def agent_models(self) -> dict[str, str]:
        """Model name of each agent, after applying the per-specialist overrides."""
        return {
            "root": self.model_root,
            "reservas": self.model_reservas or self.model_specialist,
            "visitantes": self.model_visitantes or self.model_specialist,
            "regulamento": self.model_regulamento or self.model_specialist,
        }

    @property
    def resolved_sessions_db_url(self) -> str:
        """SQLAlchemy URL of the ADK session database (defaults to a file next to db_path)."""
        if self.sessions_db_url:
            return self.sessions_db_url
        return f"sqlite+aiosqlite:///{self.db_path.parent / 'sessions.db'}"

    @property
    def sessions_db_file(self) -> Path | None:
        """Filesystem path of the session database when it is a SQLite URL."""
        url = self.resolved_sessions_db_url
        prefix = "sqlite+aiosqlite:///"
        return Path(url[len(prefix) :]) if url.startswith(prefix) else None


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
