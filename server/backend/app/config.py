"""Typed configuration kept deliberately small so the API boots in demo mode."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    secret: str
    database_url: str
    database_path: Path | None
    database_engine: str
    demo_mode: bool
    gemini_api_key: str | None
    gemini_model: str
    cors_origins: list[str]
    public_base_url: str
    cookie_secure: bool
    icpac_base: str
    http_timeout_s: float
    snapshot_ttl_min: int
    blob_read_write_token: str | None


def _database_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite:///"):
        return None
    path = Path(database_url.removeprefix("sqlite:///"))
    return path if path.is_absolute() else Path.cwd() / path


def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "sqlite:///var/linda.db")
    database_path = _database_path(database_url)
    return Settings(
        secret=os.getenv("LINDA_SECRET", "linda-local-development-secret"),
        database_url=database_url,
        database_path=database_path,
        database_engine="sqlite" if database_path else "postgres",
        demo_mode=os.getenv("DEMO_MODE", "true").lower() == "true",
        gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        cors_origins=[
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173",
            ).split(",")
        ],
        public_base_url=os.getenv("PUBLIC_BASE_URL", "http://localhost:8000"),
        cookie_secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        icpac_base=os.getenv("ICPAC_BASE", "https://eatriggersthresholds.icpac.net").rstrip("/"),
        http_timeout_s=float(os.getenv("HTTP_TIMEOUT_S", "8")),
        snapshot_ttl_min=int(os.getenv("SNAPSHOT_TTL_MIN", "30")),
        # Vercel reserves BLOB_READ_WRITE_TOKEN for stores attached directly to a
        # project. The API uses a scoped copy so it can access the private store
        # attached to the frontend project without exposing it to the browser.
        blob_read_write_token=(
            os.getenv("LINDA_BLOB_READ_WRITE_TOKEN")
            or os.getenv("BLOB_READ_WRITE_TOKEN")
            or None
        ),
    )


settings = get_settings()
if settings.database_path:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_ROOT = settings.database_path.parent / "exports"
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
else:
    EXPORT_ROOT = None
CONTENT_ROOT = Path(__file__).resolve().parents[1] / "content"
