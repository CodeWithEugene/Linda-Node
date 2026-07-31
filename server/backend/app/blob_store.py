"""Private Vercel Blob storage for immutable generated artifacts."""

from __future__ import annotations

import asyncio
from pathlib import Path

from .config import EXPORT_ROOT, settings

try:
    from vercel.blob import AsyncBlobClient
except ImportError:  # pragma: no cover - exercised only by a bare local checkout
    AsyncBlobClient = None  # type: ignore[assignment]


def _run(coroutine):
    """Export generation runs in FastAPI's synchronous worker thread."""
    return asyncio.run(coroutine)


async def _put(pathname: str, payload: bytes, content_type: str) -> str:
    if AsyncBlobClient is None or not settings.blob_read_write_token:
        raise RuntimeError("Vercel Blob storage is not configured")
    client = AsyncBlobClient()
    try:
        result = await client.put(
            pathname,
            payload,
            access="private",
            content_type=content_type,
            add_random_suffix=False,
            overwrite=False,
            token=settings.blob_read_write_token,
        )
        return result.url
    finally:
        await client.aclose()


async def _get(url: str) -> bytes:
    if AsyncBlobClient is None or not settings.blob_read_write_token:
        raise RuntimeError("Vercel Blob storage is not configured")
    client = AsyncBlobClient()
    try:
        result = await client.get(url, access="private", token=settings.blob_read_write_token)
        return result.content
    finally:
        await client.aclose()


def store_export(case_id: str, export_id: str, suffix: str, payload: bytes, content_type: str) -> str:
    if settings.database_engine == "postgres":
        return _run(_put(f"exports/{case_id}/{export_id}.{suffix}", payload, content_type))
    if EXPORT_ROOT is None:
        raise RuntimeError("Local export storage is not configured")
    folder = EXPORT_ROOT / case_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{export_id}.{suffix}"
    path.write_bytes(payload)
    return str(path)


def read_export(location: str) -> bytes:
    if location.startswith("https://"):
        return _run(_get(location))
    path = Path(location)
    if not path.is_file():
        raise FileNotFoundError(location)
    return path.read_bytes()
