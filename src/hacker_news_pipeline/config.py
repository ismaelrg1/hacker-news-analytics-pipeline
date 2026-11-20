from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="HN_PIPELINE_",
        extra="ignore",
    )

    log_level: str = "INFO"

    # Hacker news
    hacker_news_base_url: str = "https://hacker-news.firebaseio.com/v0"
    http_timeout_seconds: int = Field(default=10, gt=0)

    # DB
    database_url: str
