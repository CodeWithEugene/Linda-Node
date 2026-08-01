from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class BlockerRequest(BaseModel):
    code: str = Field(min_length=3, max_length=80)
    note: str = Field(min_length=3, max_length=1000)


class RevokeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)


class IntegrationKeyRequest(BaseModel):
    label: str = Field(min_length=2, max_length=100)


class WebhookRequest(BaseModel):
    url: str
    events: list[Literal["activation.approved", "activation.revoked"]]
    secret: str = Field(min_length=16, max_length=256)


class SnapshotResponse(BaseModel):
    id: str
    adapter: str
    endpoint_url: str
    retrieved_at: datetime
    payload: dict[str, Any]
    payload_sha256: str
    schema_ok: bool
    freshness: str


class VerificationResponse(BaseModel):
    mode: Literal["exercise"] = "exercise"
    disclaimer: str
    chain: dict[str, Any]
    signatures: dict[str, Any]
