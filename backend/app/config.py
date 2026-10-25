from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cadence:cadence@localhost:5432/cadence"
    cron_secret: str = "change-me"
    cors_origin: str = "http://localhost:3000"

    @field_validator("database_url")
    @classmethod
    def use_asyncpg_driver(cls, url: str) -> str:
        """Accept a plain Neon/Render URL and make it work with SQLAlchemy + asyncpg.

        Neon gives `postgresql://...?sslmode=require`; asyncpg wants `ssl=require` and does not
        understand `channel_binding`.
        """
        parts = urlsplit(url)
        if parts.scheme in ("postgres", "postgresql"):
            parts = parts._replace(scheme="postgresql+asyncpg")
        query = [
            ("ssl" if key == "sslmode" else key, value)
            for key, value in parse_qsl(parts.query)
            if key != "channel_binding"
        ]
        return urlunsplit(parts._replace(query=urlencode(query)))


settings = Settings()
