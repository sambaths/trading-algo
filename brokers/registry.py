from __future__ import annotations

from typing import Callable, Dict

from .core.interface import BrokerDriver
import logging



class BrokerRegistry:
    _registry: Dict[str, Callable[[], BrokerDriver]] = {}

    @classmethod
    def register(cls, name: str, factory: Callable[[], BrokerDriver]) -> None:
        cls._registry[name.lower()] = factory

    @classmethod
    def create(cls, name: str) -> BrokerDriver:
        key = name.lower()
        if key not in cls._registry:
            # Attempt to auto-register defaults
            try:
                register_default_brokers()
            except Exception:
                pass
        if key not in cls._registry:
            raise ValueError(f"Unknown broker '{name}'. Registered: {list(cls._registry)}")
        return cls._registry[key]()


def register_default_brokers() -> None:
    try:
        from .integrations.fyers.driver import FyersDriver

        BrokerRegistry.register("fyers", lambda: FyersDriver())
    except Exception:
        logging.error("Error registering fyers driver", exc_info=True)
        pass

    try:
        from .integrations.zerodha.driver import ZerodhaDriver

        BrokerRegistry.register("zerodha", lambda: ZerodhaDriver())
    except Exception:
        logging.error("Error registering zerodha driver", exc_info=True)
        pass

    try:
        from .integrations.fyrodha.driver import FyrodhaDriver

        BrokerRegistry.register("fyrodha", lambda: FyrodhaDriver())
    except Exception:
        logging.error("Error registering fyrodha driver", exc_info=True)
        pass


