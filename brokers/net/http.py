from __future__ import annotations

from typing import Any, Dict, Optional

from ..core.errors import HTTPError


DEFAULT_TIMEOUT = 15


def _requests():  # lazy import to avoid hard dependency if unused
    try:  # pragma: no cover - optional dependency
        import requests  # type: ignore

        return requests
    except Exception as e:  # pragma: no cover
        raise HTTPError("'requests' is required for HTTP operations") from e


def get_json(url: str, *, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    requests = _requests()
    try:
        r = requests.get(url, headers=headers, params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPError(f"GET {url} failed: {e}") from e


def post_json(url: str, *, headers: Optional[Dict[str, str]] = None, json: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    requests = _requests()
    try:
        r = requests.post(url, headers=headers, json=json, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:  # noqa: BLE001
        raise HTTPError(f"POST {url} failed: {e}") from e


