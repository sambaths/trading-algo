from __future__ import annotations

from .registry import symbol_registry
from ..core.enums import Exchange


def _fyers_resolver(internal: str) -> str:
    if ":" not in internal:
        internal = f"{Exchange.NSE.value}:{internal}"
    exch, sym = internal.split(":", 1)
    sym_u = sym.upper()
    index_map = {
        "NIFTY 50": "NIFTY50-INDEX",
        "NIFTY BANK": "NIFTYBANK-INDEX",
        "FINNIFTY": "FINNIFTY-INDEX",
    }
    if sym_u in index_map:
        return f"{exch}:{index_map[sym_u]}"
    if sym_u.endswith("CE") or sym_u.endswith("PE") or "FUT" in sym_u or sym_u.endswith("-INDEX"):
        return f"{exch}:{sym}"
    if not sym_u.endswith("-EQ"):
        return f"{exch}:{sym}-EQ"
    return f"{exch}:{sym}"


def _zerodha_resolver(internal: str) -> str:
    if ":" not in internal:
        internal = f"{Exchange.NSE.value}:{internal}"
    exch, sym = internal.split(":", 1)
    sym_u = sym.upper()
    fyers_index_to_zerodha = {
        "NIFTY50-INDEX": "NIFTY 50",
        "NIFTYBANK-INDEX": "NIFTY BANK",
        "FINNIFTY-INDEX": "FINNIFTY",
    }
    if sym_u in fyers_index_to_zerodha:
        return f"{exch}:{fyers_index_to_zerodha[sym_u]}"
    if sym_u.endswith("-EQ"):
        sym = sym[:-3]
    return f"{exch}:{sym}"


# Register default resolvers
symbol_registry.register_resolver("fyers", _fyers_resolver)
symbol_registry.register_resolver("zerodha", _zerodha_resolver)


