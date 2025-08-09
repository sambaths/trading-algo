from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional

from .schemas import (
    BrokerCapabilities,
    OrderRequest,
    OrderResponse,
    Position,
    Funds,
    Quote,
    Instrument,
)


class BrokerDriver(ABC):
    """Abstract broker driver interface to be implemented per broker."""

    def __init__(self) -> None:
        self.capabilities: BrokerCapabilities = BrokerCapabilities()

    # --- Capability ---
    def get_capabilities(self) -> BrokerCapabilities:
        return self.capabilities

    # --- Account ---
    @abstractmethod
    def get_funds(self) -> Funds:  # pragma: no cover - abstract
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> List[Position]:  # pragma: no cover - abstract
        raise NotImplementedError

    def get_position(self, symbol: str, exchange: Optional[str] = None) -> Optional[Position]:
        positions = self.get_positions()
        for p in positions:
            if p.symbol == symbol and (exchange is None or p.exchange.value == exchange):
                return p
        return None

    # --- Orders ---
    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResponse:  # pragma: no cover - abstract
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> OrderResponse:  # pragma: no cover - abstract
        raise NotImplementedError

    @abstractmethod
    def modify_order(self, order_id: str, updates: Dict[str, Any]) -> OrderResponse:  # pragma: no cover - abstract
        raise NotImplementedError

    @abstractmethod
    def get_orderbook(self) -> List[Dict[str, Any]]:  # pragma: no cover - abstract
        raise NotImplementedError

    @abstractmethod
    def get_tradebook(self) -> List[Dict[str, Any]]:  # pragma: no cover - abstract
        raise NotImplementedError

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        for order in self.get_orderbook():
            if str(order.get("order_id") or order.get("id")) == str(order_id):
                return order
        return None

    # --- Market data ---
    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:  # pragma: no cover - abstract
        raise NotImplementedError

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        result: Dict[str, Quote] = {}
        for s in symbols:
            try:
                result[s] = self.get_quote(s)
            except Exception:
                continue
        return result

    @abstractmethod
    def get_history(self, symbol: str, interval: str, start: str, end: str) -> List[Dict[str, Any]]:  # pragma: no cover - abstract
        raise NotImplementedError

    # --- Instruments ---
    def download_instruments(self) -> None:  # Optional
        return None

    def get_instruments(self) -> List[Instrument]:  # Optional
        return []

    # --- Option chain ---
    def get_option_chain(self, underlying: str, exchange: str, **kwargs: Any) -> List[Dict[str, Any]]:  # Optional
        raise NotImplementedError

    # --- Websocket ---
    def connect_websocket(
        self,
        *,
        on_ticks: Any | None = None,
        on_connect: Any | None = None,
        on_error: Any | None = None,
        on_close: Any | None = None,
        on_reconnect: Any | None = None,
        on_noreconnect: Any | None = None,
    ) -> None:  # Optional
        return None

    def symbols_to_subscribe(self, symbols: Iterable[str]) -> None:  # Optional
        return None

    def connect_order_websocket(
        self,
        *,
        on_order_update: Any | None = None,
        on_trades: Any | None = None,
        on_positions: Any | None = None,
        on_general: Any | None = None,
        on_error: Any | None = None,
        on_close: Any | None = None,
        on_connect: Any | None = None,
    ) -> None:  # Optional
        return None

    def unsubscribe(self, symbols: Iterable[str]) -> None:  # Optional
        return None

    # --- Advanced orders ---
    def place_gtt_order(self, *args: Any, **kwargs: Any) -> OrderResponse:  # Optional broker-specific signature
        raise NotImplementedError

    def place_bracket_order(self, *args: Any, **kwargs: Any) -> OrderResponse:
        raise NotImplementedError

    def place_cover_order(self, *args: Any, **kwargs: Any) -> OrderResponse:
        raise NotImplementedError

    def place_basket_orders(self, requests: List[OrderRequest]) -> List[OrderResponse]:
        raise NotImplementedError

    def place_multileg_order(self, *args: Any, **kwargs: Any) -> OrderResponse:
        raise NotImplementedError

    # --- Margins ---
    def get_margins_required(self, orders: List[Dict[str, Any]]) -> Any:
        raise NotImplementedError

    def get_span_margin(self, orders: List[Dict[str, Any]]) -> Any:
        raise NotImplementedError

    def get_multiorder_margin(self, orders: List[Dict[str, Any]]) -> Any:
        raise NotImplementedError

    # --- Profile / User ---
    def get_profile(self) -> Dict[str, Any]:
        raise NotImplementedError

    # --- Positions utils ---
    def exit_positions(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def convert_position(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


