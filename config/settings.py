from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import EmailStr, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Personal AI Assistant"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_chat_model: str = Field(default="gemini-3.1-flash-lite", alias="GEMINI_CHAT_MODEL")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-2",
        alias="GEMINI_EMBEDDING_MODEL",
    )

    # Your inbox — the address where you want to receive visitor messages / feedback
    contact_email: EmailStr | None = Field(default=None, alias="CONTACT_EMAIL")
    # Sender account — the Gmail that actually delivers the notification email
    gmail_address: str = Field(default="", alias="GMAIL_ADDRESS")
    gmail_app_password: str = Field(default="", alias="GMAIL_APP_PASSWORD")

    chroma_persist_directory: Path = Field(
        default=ROOT_DIR / "db" / "chroma",
        alias="CHROMA_PERSIST_DIRECTORY",
    )
    sqlite_database: Path = Field(
        default=ROOT_DIR / "db" / "app.db",
        alias="SQLITE_DATABASE",
    )
    generated_dir: Path = Field(default=ROOT_DIR / "generated", alias="GENERATED_DIR")
    data_dir: Path = Field(default=ROOT_DIR / "data", alias="DATA_DIR")
    log_dir: Path = Field(default=ROOT_DIR / "logs", alias="LOG_DIR")

    top_k: int = Field(default=5, alias="TOP_K", ge=1, le=20)
    chunk_size: int = Field(default=800, alias="CHUNK_SIZE", ge=200, le=4000)
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP", ge=0, le=1000)
    max_upload_size_mb: int = Field(default=10, alias="MAX_UPLOAD_SIZE_MB", ge=1, le=50)
    max_chunks_per_query: int = Field(default=12, alias="MAX_CHUNKS_PER_QUERY", ge=1, le=50)
    collection_name: str = Field(default="personal_knowledge", alias="CHROMA_COLLECTION_NAME")
    web_search_enabled: bool = Field(default=False, alias="WEB_SEARCH_ENABLED")
    log_file_name: str = Field(default="app.log", alias="LOG_FILE_NAME")
    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="PA-AI", alias="LANGSMITH_PROJECT")
    langsmith_endpoint: str = Field(
        default="https://api.smith.langchain.com",
        alias="LANGSMITH_ENDPOINT",
    )
    # When False (production), only the Chat page is shown.
    # Set DEV_MODE=true to also expose Knowledge Base, Generated Files, Settings, and About.
    dev_mode: bool = Field(default=False, alias="DEV_MODE")

    @computed_field
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @computed_field
    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".pdf", ".docx", ".txt", ".md", ".markdown", ".json", ".csv")

    @computed_field
    @property
    def allowed_mime_types(self) -> tuple[str, ...]:
        return (
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
            "application/json",
            "text/csv",
        )

    @computed_field
    @property
    def log_file(self) -> Path:
        return self.log_dir / self.log_file_name

    def ensure_directories(self) -> None:
        self.chroma_persist_directory.mkdir(parents=True, exist_ok=True)
        self.sqlite_database.parent.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def email_enabled(self) -> bool:
        """
        Email is considered enabled when the receive address is set.
        If only CONTACT_EMAIL is set (no separate sender), the app uses
        the same address as both sender and recipient (self-send pattern).
        """
        return bool(self.contact_email)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def langsmith_enabled(self) -> bool:
        return self.langsmith_tracing and bool(self.langsmith_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


def reset_settings_cache() -> None:
    get_settings.cache_clear()
