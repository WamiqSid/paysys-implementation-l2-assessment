from pydantic_settings import BaseSettings, SettingsConfigDict


class SupportSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    minipay_api_url: str = "http://127.0.0.1:8080"
    minipay_api_key: str = "minipay-dev-key"
    minipay_timeout_seconds: float = 8.0
    database_url: str | None = None
