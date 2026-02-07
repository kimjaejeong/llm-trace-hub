from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LLM Trace Hub"
    environment: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/tracehub"
    internal_api_key_seed: str = "dev-seed"
    webhook_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
