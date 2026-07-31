"""Cookie session authentication and role dependencies.

JWT uses a compact HS256 implementation to avoid coupling the demo's trust path
to a second authentication framework. Passwords use Argon2 when installed.
"""

from __future__ import annotations

import base64
import hmac
import json
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import Depends, HTTPException, Request, Response, status

from .config import settings
from .db import connection, row_to_dict, verify_password
from .domain import canonical_json

_attempts: dict[str, deque[float]] = defaultdict(deque)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def make_session(user_id: str) -> str:
    header = _b64(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64(canonical_json({"sub": user_id, "exp": int(time.time()) + 86_400}).encode())
    signing_input = f"{header}.{payload}".encode()
    signature = _b64(hmac.new(settings.secret.encode(), signing_input, "sha256").digest())
    return f"{header}.{payload}.{signature}"


def read_session(token: str) -> str | None:
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(settings.secret.encode(), f"{header}.{payload}".encode(), "sha256").digest())
        if not hmac.compare_digest(expected, signature):
            return None
        data = json.loads(_unb64(payload))
        return data["sub"] if data["exp"] >= int(time.time()) else None
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in ("id", "email", "display_name", "role", "org")}


def login(email: str, password: str, request: Request, response: Response) -> dict[str, Any]:
    client = request.client.host if request.client else "unknown"
    recent = _attempts[client]
    cutoff = time.time() - 300
    while recent and recent[0] < cutoff:
        recent.popleft()
    if len(recent) >= 5:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts. Try again in five minutes.")
    with connection() as conn:
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone())
    if not user or not verify_password(user["password_hash"], password):
        recent.append(time.time())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    response.set_cookie("linda_session", make_session(user["id"]), httponly=True, samesite="lax", secure=settings.cookie_secure, max_age=86_400)
    return public_user(user)


def current_user(request: Request) -> dict[str, Any]:
    user_id = read_session(request.cookies.get("linda_session", ""))
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Sign in is required")
    with connection() as conn:
        user = row_to_dict(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Session is no longer valid")
    return public_user(user)


def require_role(*roles: str):
    def dependency(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Your role is not permitted to perform this action")
        return user

    return dependency
