from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/minipay.db"
    api_key: str = "minipay-dev-key"
    log_level: str = "INFO"
    # Deliberate defect flag used to reproduce INCIDENT-001.
    buggy_search: bool = False
    app_name: str = "minipay-api"


@lru_cache
def get_settings() -> Settings:
    return Settings()
