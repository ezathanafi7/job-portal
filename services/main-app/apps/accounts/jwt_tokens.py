
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

TokenType = Literal["access", "refresh"]
ALGORITHM = "RS256"
# Every token we accept must contain all of these fields ("claims").
REQUIRED_CLAIMS = ["iss", "aud", "sub", "type", "jti", "iat", "exp"]


class TokenError(Exception):
    """Raised when a token can't be created or isn't valid."""


@dataclass(frozen=True)
class JWTConfig:
    public_key: str
    issuer: str          # who created the token, e.g. "job-portal-main"
    audience: str        # who the token is meant for, e.g. "job-portal"
    access_ttl: timedelta
    refresh_ttl: timedelta
    private_key: str | None = None  # None = this service can only VERIFY tokens
    leeway_seconds: int = 10         # allow small clock differences between servers


@dataclass(frozen=True)
class EncodedToken:
    token: str
    jti: str               # unique ID of this token
    expires_at: datetime


def encode_token(
    config: JWTConfig,
    *,
    subject: str,
    token_type: TokenType,
    claims: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> EncodedToken:
    """Create a signed token for `subject` (the user's ID)."""
    if not config.private_key:
        raise TokenError("This service is not configured to issue tokens.")

    now = now or datetime.now(UTC)
    ttl = config.access_ttl if token_type == "access" else config.refresh_ttl
    expires_at = now + ttl
    jti = uuid.uuid4().hex

    payload: dict[str, Any] = {
        **(claims or {}),          # extra data first (e.g. role)...
        "iss": config.issuer,      # ...then our standard claims, so extra data
        "aud": config.audience,    #    can never overwrite them
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),         # issued at
        "exp": int(expires_at.timestamp()),  # expires at
    }
    token = jwt.encode(payload, config.private_key, algorithm=ALGORITHM)
    return EncodedToken(token=token, jti=jti, expires_at=expires_at)


def decode_token(config: JWTConfig, token: str, *, expected_type: TokenType) -> dict[str, Any]:
    """Check signature, expiry, issuer, audience and type. Returns the payload if valid."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            config.public_key,
            # IMPORTANT: we fix the algorithm ourselves. Never trust the algorithm
            # written inside the token, or attackers can send "alg: none" tokens.
            algorithms=[ALGORITHM],
            audience=config.audience,
            issuer=config.issuer,
            leeway=config.leeway_seconds,
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid token.") from exc

    # Stops someone using a refresh token as an access token (or the other way round).
    if payload.get("type") != expected_type:
        raise TokenError("Invalid token type.")
    return payload


def generate_rsa_keypair(key_size: int = 2048) -> tuple[str, str]:
    """Create a new (private_key, public_key) pair as PEM text."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def normalize_pem(value: str | None) -> str | None:
    """Keys are stored on ONE line in .env, with \\n instead of real line breaks.
    This turns them back into proper multi-line keys."""
    if not value:
        return None
    return value.replace("\\n", "\n").strip() + "\n"