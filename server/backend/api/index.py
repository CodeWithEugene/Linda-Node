"""Vercel's FastAPI function entrypoint.

The application itself lives in ``app.main`` so it can also run under the
container image used for local and non-serverless deployments.
"""

from app.main import app  # noqa: F401 - Vercel resolves this module-level ASGI app.
