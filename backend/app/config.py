from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./var/linda.db"
    secret_key: str = "linda-local-development-secret"
    demo_mode: bool = True
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    icpac_timeout_seconds: float = 10.0
    integration_rate_limit_per_minute: int = 60
    content_dir: Path = Path("backend/content")
    export_dir: Path = Path("var/exports")

    model_config = SettingsConfigDict(env_file=".env", env_prefix="LINDA_", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
