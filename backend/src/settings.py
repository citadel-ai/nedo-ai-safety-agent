import os
from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Env(str, Enum):
    DEV = "dev"
    STG = "stg"
    PROD = "prod"


class Context(str, Enum):
    LOCAL = "local"
    CI = "ci"
    CLOUD = "cloud"


class Settings(BaseSettings):
    app_env: Env = Field(default=Env.DEV, alias="APP_ENV")
    app_context: Context = Field(default=Context.LOCAL, alias="APP_CONTEXT")

    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")

    agent_model: str = Field(default="gemini-2.5-flash", alias="AGENT_MODEL")
    agent_temperature: float = Field(default=0.3, alias="AGENT_TEMPERATURE")
    agent_seed: int = Field(default=42, alias="AGENT_SEED")
    agent_max_tokens: int = Field(default=2048, alias="AGENT_MAX_TOKENS")
    vertex_ai_location: str = Field(default="asia-northeast1", alias="VERTEX_AI_LOCATION")

    langfuse_enabled: bool = Field(default=True, alias="LANGFUSE_ENABLED")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_host: str = Field(default="", alias="LANGFUSE_HOST")

    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_cse_id: str = Field(default="", alias="GOOGLE_CSE_ID")
    google_cloud_project: str = Field(default="", alias="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: str = Field(
        default="",
        alias="GOOGLE_APPLICATION_CREDENTIALS",
    )

    embedding_provider: str = Field(default="google", alias="EMBEDDING_PROVIDER")

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env.local")

    @property
    def use_json_log(self) -> bool:
        in_cloud_run = os.getenv("K_SERVICE") is not None
        return in_cloud_run or self.app_env in (Env.STG, Env.PROD)


def load_settings() -> Settings:
    s = Settings()

    if os.getenv("K_SERVICE"):
        s.app_context = Context.CLOUD

    return s
