from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cadence:cadence@localhost:5432/cadence"
    cron_secret: str = "change-me"
    cors_origin: str = "http://localhost:3000"


settings = Settings()
