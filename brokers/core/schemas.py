from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import Exchange, OrderType, ProductType, TransactionType, Validity


@dataclass
class BrokerCapabilities:
    supports_historical: bool = True
    supports_quotes: bool = True
    supports_funds: bool = True
    supports_positions: bool = True
    supports_place_order: bool = True
    supports_modify_order: bool = True
    supports_cancel_order: bool = True
    supports_tradebook: bool = True
    supports_orderbook: bool = True
    supports_websocket: bool = True
    supports_order_websocket: bool = False
    supports_master_contract: bool = False
    supports_option_chain: bool = False
    supports_gtt: bool = False
    supports_bracket_order: bool = False
    supports_cover_order: bool = False
    supports_multileg_order: bool = False
    supports_basket_orders: bool = False


@dataclass
class OrderRequest:
    symbol: str
    exchange: Exchange
    quantity: int
    order_type: OrderType
    transaction_type: TransactionType
    product_type: ProductType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    validity: Validity = Validity.DAY
    tag: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderResponse:
    status: str
    order_id: Optional[str]
    message: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "order_id": self.order_id,
            "message": self.message,
            "raw": self.raw,
        }


@dataclass
class Position:
    symbol: str
    exchange: Exchange
    quantity_total: int
    quantity_available: int
    average_price: float
    pnl: float = 0.0
    product_type: ProductType = ProductType.INTRADAY
    raw: Optional[Dict[str, Any]] = None


@dataclass
class Funds:
    equity: float
    available_cash: float
    used_margin: float
    net: float
    raw: Optional[Dict[str, Any]] = None


@dataclass
class Quote:
    symbol: str
    exchange: Exchange
    last_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class Instrument:
    symbol: str
    exchange: Exchange
    name: Optional[str] = None
    lot_size: Optional[int] = None
    tick_size: Optional[float] = None
    instrument_token: Optional[str] = None
    segment: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


