"""Core enums, schemas, errors, interfaces, and gateway facade."""

from .enums import Exchange, OrderType, ProductType, TransactionType, Validity
from .schemas import (
    OrderRequest,
    OrderResponse,
    Position,
    Funds,
    Quote,
    Instrument,
    BrokerCapabilities,
)
from .errors import (
    BrokerError,
    AuthError,
    RateLimitError,
    TimeoutError,
    UnsupportedOperationError,
    MarginUnavailableError,
    ValidationError,
    HTTPError,
)
from .interface import BrokerDriver
from .gateway import BrokerGateway

__all__ = [
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
    # Errors
    "BrokerError",
    "AuthError",
    "RateLimitError",
    "TimeoutError",
    "UnsupportedOperationError",
    "MarginUnavailableError",
    "ValidationError",
    "HTTPError",
    # Interface / Facade
    "BrokerDriver",
    "BrokerGateway",
]


