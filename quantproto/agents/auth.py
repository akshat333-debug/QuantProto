"""JWT authentication for agent-to-agent communication.

Uses HS256 with configurable expiry. Tokens carry agent_id and issued_at.
"""

from __future__ import annotations

import time
from typing import Any

import jwt


DEFAULT_SECRET = "quantproto-dev-secret-change-in-prod"
ALGORITHM = "HS256"
DEFAULT_EXPIRY_SECONDS = 300  # 5 minutes


def sign_token(
    agent_id: str,
    secret: str = DEFAULT_SECRET,
    expiry_seconds: int = DEFAULT_EXPIRY_SECONDS,
) -> str:
    """Create a signed JWT for agent communication.

    Parameters
    ----------
    agent_id : identifier of the issuing agent.
    secret : HMAC secret key.
    expiry_seconds : token validity duration.

    Returns
    -------
    Encoded JWT string.
    """
    now = time.time()
    payload = {
        "agent_id": agent_id,
        "iat": now,
        "exp": now + expiry_seconds,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def verify_token(
    token: str,
    secret: str = DEFAULT_SECRET,
) -> dict[str, Any]:
    """Verify and decode a JWT.

    Parameters
    ----------
    token : encoded JWT string.
    secret : HMAC secret key (must match signing key).

    Returns
    -------
    Decoded payload dict.

    Raises
    ------
    jwt.ExpiredSignatureError : if token has expired.
    jwt.InvalidSignatureError : if signature doesn't match.
    jwt.DecodeError : if token is malformed.
    """
    return jwt.decode(token, secret, algorithms=[ALGORITHM])
