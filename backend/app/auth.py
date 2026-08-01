from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import jwt
from argon2 import PasswordHasher
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

password_hasher = PasswordHasher()


def password_hash(value: str) -> str:
    return password_hasher.hash(value)


def password_matches(value: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, value)
    except Exception:
        return False


def issue_token(user: User) -> str:
    payload = {"sub": user.id, "role": user.role, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def current_user(
    authorization: str | None = Header(default=None),
    x_demo_user: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if settings.demo_mode and x_demo_user:
        user = db.query(User).filter(User.email == x_demo_user).one_or_none()
        if user:
            return user
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    try:
        token = jwt.decode(authorization[7:], settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session") from exc
    user = db.get(User, token["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unknown user")
    return user


def require_roles(*roles: str):
    def guard(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role is not permitted for this operation")
        return user
    return guard


def new_integration_key() -> tuple[str, str]:
    raw = "linda_" + secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def key_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
