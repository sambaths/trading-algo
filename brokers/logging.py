from __future__ import annotations

import logging
import os
from typing import Optional


def get_logger(name: str, *, level: Optional[int] = None) -> logging.Logger:
    """Create or return a configured logger.

    Policy:
    - INFO: trade entries/exits, upcoming actions, market analysis milestones, errors/warnings, P/L
    - DEBUG: initialization, registrations, expected operations
    - Quiet by default; controllable via BROKERS2_LOG_LEVEL env.
    """

    logger = logging.getLogger(name)
    if logger.handlers:  # already configured
        return logger

    env_level = os.getenv("BROKERS2_LOG_LEVEL", "INFO").upper()
    resolved_level = level or getattr(logging, env_level, logging.INFO)
    logger.setLevel(resolved_level)
    handler = logging.StreamHandler()
    handler.setLevel(resolved_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


