"""
brokers2: Next-generation broker abstraction layer.

This package provides a clean, typed, and extensible broker-agnostic API:
- Core domain models and interface in `brokers2.core`
- Symbol normalization and per-broker resolvers in `brokers2.symbols`
- Enum/string mappings in `brokers2.mappings`
- Pluggable broker drivers in `brokers2.integrations`
- A simple facade `BrokerGateway` and a `BrokerRegistry` to construct drivers

Environment variables are loaded via python-dotenv when available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Best-effort .env loading
try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:  # pragma: no cover - be silent if dotenv is missing
    pass

from .core.gateway import BrokerGateway
from .registry import BrokerRegistry
from .core.enums import Exchange, OrderType, ProductType, TransactionType, Validity
from .core.schemas import (
    OrderRequest,
    OrderResponse,
    Position,
    Funds,
    Quote,
    Instrument,
    BrokerCapabilities,
)

# Ensure default symbol resolvers are registered
from .symbols import resolvers as _symbol_resolvers  # noqa: F401

__all__ = [
    "BrokerGateway",
    "BrokerRegistry",
    # Enums
    "Exchange",
    "OrderType",
    "ProductType",
    "TransactionType",
    "Validity",
    # Schemas
    "OrderRequest",
    "OrderResponse",
    "Position",
    "Funds",
    "Quote",
    "Instrument",
    "BrokerCapabilities",
]


