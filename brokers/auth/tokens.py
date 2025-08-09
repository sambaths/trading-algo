from __future__ import annotations

import os
from typing import Optional


def get_access_token(*keys: str) -> Optional[str]:
    """Return first non-empty env value for provided keys."""

    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return None


