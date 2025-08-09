from __future__ import annotations

from ..core.errors import AuthError


def totp_now(secret: str) -> str:
    """Return current TOTP for a base32 secret using pyotp."""

    try:  # pragma: no cover - optional dependency
        import pyotp  # type: ignore
    except Exception as e:  # pragma: no cover
        raise AuthError("pyotp is required for TOTP authentication") from e
    return pyotp.TOTP(secret).now()


