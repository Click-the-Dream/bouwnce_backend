from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PushKeys(BaseModel):
    p256dh: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Base64 URL-encoded P-256 public key",
    )
    auth: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Base64 URL-encoded auth secret",
    )


class PushSubscriptionIn(BaseModel):
    """Browser ``PushSubscription`` serialized as JSON (see MDN)."""

    model_config = ConfigDict(populate_by_name=True)

    endpoint: str = Field(
        ...,
        min_length=5,
        max_length=2048,
        description="Push service endpoint (https, or http://localhost in dev)",
    )
    keys: PushKeys
    expiration_time: datetime | None = Field(
        None,
        alias="expirationTime",
        description="When the subscription expires, if the browser set one",
    )

    @field_validator("endpoint")
    @classmethod
    def _validate_endpoint_scheme(cls, v: str) -> str:
        if v.startswith("https://") or v.startswith("http://localhost"):
            return v
        raise ValueError("endpoint must be an https URL (or http://localhost in dev)")


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(
        ...,
        min_length=5,
        max_length=2048,
        description="The exact endpoint previously used to subscribe",
    )

    @field_validator("endpoint")
    @classmethod
    def _validate_endpoint_scheme(cls, v: str) -> str:
        if v.startswith("https://") or v.startswith("http://localhost"):
            return v
        raise ValueError("endpoint must be an https URL (or http://localhost in dev)")
