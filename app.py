"""Local entry point for Linda Protocol.

The application itself lives in ``backend.app.main`` so the same FastAPI
instance is used by local development, Docker, and the test suite.
"""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)
