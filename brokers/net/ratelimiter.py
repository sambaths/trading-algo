from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar, cast


F = TypeVar("F", bound=Callable[..., Any])


def rate_limited(
    *,
    calls_per_second: Optional[int] = None,
    calls_per_minute: Optional[int] = None,
    calls_per_day: Optional[int] = None,
) -> Callable[[F], F]:
    """Generic rate-limiting decorator builder using ratelimit.sleep_and_retry."""

    try:  # pragma: no cover - optional dependency
        from ratelimit import limits, sleep_and_retry  # type: ignore
    except Exception as e:  # pragma: no cover
        # If ratelimit isn't installed, return identity decorator
        def identity(func: F) -> F:
            return func

        return identity

    def decorator(func: F) -> F:
        wrapped: Callable[..., Any] = func
        if calls_per_second is not None:
            wrapped = sleep_and_retry(limits(calls=calls_per_second, period=1))(wrapped)  # type: ignore[assignment]
        if calls_per_minute is not None:
            wrapped = sleep_and_retry(limits(calls=calls_per_minute, period=60))(wrapped)  # type: ignore[assignment]
        if calls_per_day is not None:
            wrapped = sleep_and_retry(limits(calls=calls_per_day, period=86400))(wrapped)  # type: ignore[assignment]
        return cast(F, wrapped)

    return decorator


def rate_limited_fyers() -> Callable[[F], F]:
    """Preconfigured rate limiter for Fyers API calls."""

    return rate_limited(calls_per_second=9, calls_per_minute=195, calls_per_day=99900)


