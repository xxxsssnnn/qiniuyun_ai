from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI 同声传译助手"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./app.db"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"])

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
