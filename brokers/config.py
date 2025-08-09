from __future__ import annotations

import os
from typing import Optional


def getenv(key: str, default: Optional[str] = None, *aliases: str) -> Optional[str]:
    """Return first non-empty env var among key and aliases."""

    for k in (key, *aliases):
        v = os.getenv(k)
        if v not in (None, ""):
            return v
    return default


def getenv_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


