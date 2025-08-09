from __future__ import annotations

from typing import Callable, Dict

from ..core.enums import Exchange


class SymbolRegistry:
    """Normalizes and translates symbols across brokers.

    Canonical format: "<EXCHANGE>:<TRADINGSYMBOL>" (e.g., "NSE:RELIANCE").
    """

    def __init__(self) -> None:
        self._to_broker: Dict[str, Dict[str, str]] = {}
        self._from_broker: Dict[str, Dict[str, str]] = {}
        self._resolvers: Dict[str, Callable[[str], str]] = {}

    def register_mapping(self, broker: str, internal_to_broker: Dict[str, str]) -> None:
        self._to_broker[broker] = internal_to_broker
        self._from_broker[broker] = {v: k for k, v in internal_to_broker.items()}

    def to_broker_symbol(self, broker: str, internal_symbol: str) -> str:
        if broker in self._resolvers:
            return self._resolvers[broker](internal_symbol)
        return self._to_broker.get(broker, {}).get(internal_symbol, internal_symbol)

    def from_broker_symbol(self, broker: str, broker_symbol: str) -> str:
        return self._from_broker.get(broker, {}).get(broker_symbol, self.normalize(broker_symbol))

    def register_resolver(self, broker: str, resolver: Callable[[str], str]) -> None:
        self._resolvers[broker] = resolver

    @staticmethod
    def normalize(symbol: str) -> str:
        if ":" in symbol:
            exchange, s = symbol.split(":", 1)
            exchange = exchange.strip().upper()
            s = s.strip()
            if s.endswith("-EQ"):
                s = s[:-3]
            if s.endswith("-STOCK"):
                s = s[:-6]
            return f"{exchange}:{s}"
        return f"{Exchange.NSE.value}:{symbol.strip().upper()}"


symbol_registry = SymbolRegistry()


