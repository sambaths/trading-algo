from __future__ import annotations

from typing import Optional, Tuple


def prompt(text: str = "") -> str:
    """Blocking input prompt (interactive flows)."""

    return input(text)


def manual_exchange_request_token(login_url: str) -> str:
    """Guide user to open URL and paste request token."""

    print(
        "\nManual login:\n"
        f"1) Open this URL in a browser and complete login:\n{login_url}\n"
        "2) Copy the 'request_token' (or 'auth_code') from the redirected URL and paste below.\n"
    )
    token = prompt("Token: ").strip()
    if not token:
        raise ValueError("Empty token provided")
    return token


