from __future__ import annotations

import math, os
import random
import time
from datetime import datetime, timedelta
import threading
from typing import Any, Dict, List, Optional

from ...core.enums import Exchange, OrderType, ProductType, TransactionType, Validity
from ...core.errors import MarginUnavailableError, UnsupportedOperationError
from ...core.interface import BrokerDriver
from ...core.schemas import (
    BrokerCapabilities,
    Funds,
    Instrument,
    OrderRequest,
    OrderResponse,
    Position,
    Quote,
)


class FyrodhaDriver(BrokerDriver):
    """Simulated broker for testing, sourcing base prices from live quotes and
    evolving via Brownian motion. Margins proxied to Fyers endpoints for estimates.
    """

    def __init__(self) -> None:
        super().__init__()
        self.capabilities = BrokerCapabilities(
            supports_historical=True,
            supports_quotes=True,
            supports_funds=True,
            supports_positions=True,
            supports_place_order=True,
            supports_modify_order=True,
            supports_cancel_order=True,
            supports_tradebook=True,
            supports_orderbook=True,
            supports_websocket=False,
            supports_order_websocket=False,
            supports_master_contract=False,
            supports_option_chain=True,
            supports_gtt=False,
            supports_bracket_order=False,
            supports_cover_order=False,
            supports_multileg_order=True,
            supports_basket_orders=True,
        )
        self._balances: Dict[str, float] = {"cash": 1_000_000.0}
        self._positions: Dict[str, Position] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._rng = random.Random(42)

        # Use real gateways to fetch seed quotes/margins where available
        try:
            from ...core.gateway import BrokerGateway

            self._seed_fyers = BrokerGateway.from_name(os.getenv("SIMULATION_SEED_BROKER", "fyers"))
        except Exception:
            self._seed_fyers = None

        # WS simulation state
        self._ws_thread: Optional[threading.Thread] = None
        self._ws_running: bool = False
        self._ws_symbols: List[str] = []
        self._ws_on_ticks: Optional[Any] = None
        self._ws_on_connect: Optional[Any] = None
        self._ws_on_close: Optional[Any] = None
        self._ws_interval: str = "1m"
        self._ws_speed: float = 1.0  # 1 candle per second
        self._ws_history_minutes: int = 120  # stream last 120 minutes by default
        self._ws_simulate_date: Optional[str] = None  # YYYY-MM-DD

    # --- Helpers ---
    def _seed_quote(self, symbol: str) -> float:
        # Try real quote via fyers gateway; else fallback to last cached or random
        try:
            if self._seed_fyers:
                q = self._seed_fyers.get_quote(symbol)
                if q and q.last_price and q.last_price > 0:
                    return float(q.last_price)
        except Exception:
            pass
        # Basic fallback
        base = self._rng.uniform(100, 1000)
        return base

    def _bm_step(self, price: float, sigma: float = 0.015) -> float:
        # Simple geometric Brownian motion step
        dt = 1.0
        mu = 0.0
        z = self._rng.normalvariate(0.0, 1.0)
        return max(0.01, price * math.exp((mu - 0.5 * sigma * sigma) * dt + sigma * math.sqrt(dt) * z))

    # --- Account ---
    def get_funds(self) -> Funds:
        cash = self._balances.get("cash", 0.0)
        return Funds(equity=cash, available_cash=cash, used_margin=0.0, net=cash, raw={})

    def get_positions(self) -> List[Position]:
        return list(self._positions.values())

    # --- Orders ---
    def place_order(self, request: OrderRequest) -> OrderResponse:
        oid = str(int(time.time() * 1000))
        side = 1 if request.transaction_type == TransactionType.BUY else -1
        quantity = int(request.quantity)
        symbol_full = f"{request.exchange.value}:{request.symbol}"
        price = float(request.price or self._seed_quote(symbol_full))
        # Fill immediately at price
        pos_key = f"{request.exchange.value}:{request.symbol}:{request.product_type.value}"
        existing = self._positions.get(pos_key)
        if existing:
            new_qty = existing.quantity_total + side * quantity
            new_available = existing.quantity_available + side * quantity
            new_avg = existing.average_price
            if new_qty != 0:
                new_avg = (existing.average_price * existing.quantity_total + price * quantity) / max(1, existing.quantity_total + quantity)
            self._positions[pos_key] = Position(
                symbol=existing.symbol,
                exchange=existing.exchange,
                quantity_total=new_qty,
                quantity_available=new_available,
                average_price=new_avg,
                pnl=existing.pnl,
                product_type=existing.product_type,
                raw=existing.raw,
            )
        else:
            self._positions[pos_key] = Position(
                symbol=request.symbol,
                exchange=request.exchange,
                quantity_total=side * quantity,
                quantity_available=side * quantity,
                average_price=price,
                pnl=0.0,
                product_type=request.product_type,
                raw={"simulated": True},
            )
        self._orders[oid] = {"id": oid, "status": "COMPLETE", "symbol": symbol_full, "price": price, "qty": quantity, "side": side}
        # Emit order update over order socket if registered
        if getattr(self, "_on_order_update_cb", None):
            try:
                self._on_order_update_cb(None, {"event": "order_update", "status": "ok", "order_id": oid, "raw": self._orders[oid]})
            except Exception:
                pass
        return OrderResponse(status="ok", order_id=oid, raw=self._orders[oid])

    def cancel_order(self, order_id: str) -> OrderResponse:
        od = self._orders.get(order_id)
        if not od:
            return OrderResponse(status="error", order_id=order_id, message="order not found")
        od["status"] = "CANCELLED"
        if getattr(self, "_on_order_update_cb", None):
            try:
                self._on_order_update_cb(None, {"event": "order_update", "status": "cancelled", "order_id": order_id, "raw": od})
            except Exception:
                pass
        return OrderResponse(status="ok", order_id=order_id, raw=od)

    def modify_order(self, order_id: str, updates: Dict[str, Any]) -> OrderResponse:
        od = self._orders.get(order_id)
        if not od:
            return OrderResponse(status="error", order_id=order_id, message="order not found")
        od.update(updates)
        if getattr(self, "_on_order_update_cb", None):
            try:
                self._on_order_update_cb(None, {"event": "order_update", "status": "modified", "order_id": order_id, "raw": od})
            except Exception:
                pass
        return OrderResponse(status="ok", order_id=order_id, raw=od)

    def get_orderbook(self) -> List[Dict[str, Any]]:
        return list(self._orders.values())

    def get_tradebook(self) -> List[Dict[str, Any]]:
        # In simulation, all orderbook entries are treated as trades as well
        return list(self._orders.values())

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._orders.get(order_id)

    def get_profile(self) -> Dict[str, Any]:
        return {"simulated": True}

    # --- Market data ---
    def get_quote(self, symbol: str) -> Quote:
        base = self._seed_quote(symbol)
        evolved = self._bm_step(base)
        exch, tsym = symbol.split(":", 1) if ":" in symbol else ("NSE", symbol)
        return Quote(symbol=tsym.replace("-EQ", ""), exchange=Exchange[exch], last_price=evolved, raw={"seed": base, "sim": evolved})

    def get_history(self, symbol: str, interval: str, start: str, end: str) -> List[Dict[str, Any]]:
        base = self._seed_quote(symbol)
        # Generate synthetic candles at ~15m resolution unless otherwise requested
        try:
            start_dt = datetime.fromisoformat(start) if "-" in start else datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.fromisoformat(end) if "-" in end else datetime.strptime(end, "%Y-%m-%d")
        except Exception:
            start_dt = datetime.utcnow() - timedelta(days=1)
            end_dt = datetime.utcnow()
        step_minutes = 15
        if interval.lower() in ("1m", "3m", "5m"):
            step_minutes = int(interval[:-1])
        elif interval.lower() in ("30m", "60m"):
            step_minutes = int(interval[:-1])
        candles: List[Dict[str, Any]] = []
        t = base
        ts = int(start_dt.timestamp())
        while start_dt <= end_dt:
            o = t
            h = max(o, self._bm_step(o))
            l = min(o, self._bm_step(o))
            c = self._bm_step(o)
            v = int(abs(self._rng.gauss(1e5, 2e4)))
            candles.append({"ts": ts, "open": o, "high": h, "low": l, "close": c, "volume": v})
            t = c
            start_dt += timedelta(minutes=step_minutes)
            ts = int(start_dt.timestamp())
        return candles

    # --- Instruments ---
    def download_instruments(self) -> None:
        self._seed_fyers.download_instruments()

    def get_instruments(self) -> List[Instrument]:
        return self._seed_fyers.get_instruments()

    # --- Option chain ---
    def get_option_chain(self, underlying: str, exchange: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # Simulate by returning a grid of strikes around current spot
        sym = f"{exchange}:{underlying}" if ":" not in underlying else underlying
        spot = self._seed_quote(sym)
        lot = 50
        strikes = [round(spot + d, -1) for d in range(-300, 301, 50)]
        out: List[Dict[str, Any]] = []
        for k in strikes:
            out.append({"symbol": f"{exchange}:{underlying}{int(k)}CE", "strike": k, "last_price": self._bm_step(5.0)})
            out.append({"symbol": f"{exchange}:{underlying}{int(k)}PE", "strike": k, "last_price": self._bm_step(5.0)})
        return out

    # --- Websocket (not simulated in this version) ---
    def connect_websocket(self, **kwargs: Any) -> None:  # type: ignore[override]
        # Accept callbacks and optional replay config
        self._ws_on_ticks = kwargs.get("on_ticks")
        self._ws_on_connect = kwargs.get("on_connect")
        self._ws_on_close = kwargs.get("on_close")
        interval = kwargs.get("interval")
        speed = kwargs.get("speed")
        hist_minutes = kwargs.get("history_minutes")
        sim_date = kwargs.get("simulate_date")  # YYYY-MM-DD
        if isinstance(interval, str):
            self._ws_interval = interval
        if isinstance(speed, (int, float)) and speed > 0:
            self._ws_speed = float(speed)
        if isinstance(hist_minutes, int) and hist_minutes > 0:
            self._ws_history_minutes = hist_minutes
        if isinstance(sim_date, str) and len(sim_date) >= 10:
            self._ws_simulate_date = sim_date[:10]

        if self._ws_running:
            return
        self._ws_running = True
        self._ws_thread = threading.Thread(target=self._ws_loop, daemon=True)
        self._ws_thread.start()

    def _ws_loop(self) -> None:
        try:
            if callable(self._ws_on_connect):
                try:
                    self._ws_on_connect(None)
                except Exception:
                    pass
            # Streaming loop: repeatedly replay a moving window
            while self._ws_running:
                symbols = list(self._ws_symbols)
                if not symbols:
                    time.sleep(0.1)
                    continue
                # Build history window (override with simulate_date if provided)
                if self._ws_simulate_date:
                    start = self._ws_simulate_date
                    end = self._ws_simulate_date
                else:
                    end_dt = datetime.utcnow()
                    start_dt = end_dt - timedelta(minutes=self._ws_history_minutes)
                    start = start_dt.strftime("%Y-%m-%d")
                    end = end_dt.strftime("%Y-%m-%d")

                # Fetch history via seed gateway
                symbol_to_candles: Dict[str, List[Dict[str, Any]]] = {}
                for s in symbols:
                    try:
                        if self._seed_fyers:
                            candles = self._seed_fyers.get_history(s, self._ws_interval, start, end)
                        else:
                            candles = self.get_history(s, self._ws_interval, start, end)
                        symbol_to_candles[s] = candles or []
                    except Exception:
                        symbol_to_candles[s] = []

                # Iterate by index (assume roughly aligned lengths)
                # Start at 09:15 local and advance by interval
                try:
                    if isinstance(self._ws_interval, str) and self._ws_interval.endswith("m"):
                        interval_minutes = max(1, int(self._ws_interval[:-1]))
                    else:
                        interval_minutes = 1
                except Exception:
                    interval_minutes = 1
                base_day = datetime.now().date()
                if self._ws_simulate_date:
                    try:
                        base_day = datetime.strptime(self._ws_simulate_date, "%Y-%m-%d").date()
                    except Exception:
                        base_day = datetime.now().date()
                base_start_dt = datetime(base_day.year, base_day.month, base_day.day, 9, 15, 0)

                max_len = max((len(v) for v in symbol_to_candles.values()), default=0)
                for i in range(max_len):
                    if not self._ws_running:
                        break
                    ts_mapped = int((base_start_dt + timedelta(minutes=i * interval_minutes)).timestamp())
                    for s, series in symbol_to_candles.items():
                        if i >= len(series):
                            continue
                        c = series[i]
                        o = float(c.get("open") or 0.0) or self._seed_quote(s)
                        h = float(c.get("high") or o)
                        l = float(c.get("low") or o)
                        cl = float(c.get("close") or o)
                        price = cl if cl else o
                        # Small BM perturbation
                        price = self._bm_step(price, sigma=0.003)

                        tick = {
                            "symbol": s,
                            "ltp": price,
                            "last_price": price,
                            "open": o,
                            "high": h,
                            "low": l,
                            "close": cl,
                            "ohlc": {"open": o, "high": h, "low": l, "close": cl},
                            "volume": c.get("volume"),
                            "timestamp": ts_mapped,
                        }
                        if callable(self._ws_on_ticks):
                            try:
                                # Emit one symbol at a time as dict
                                self._ws_on_ticks(None, tick)
                            except Exception:
                                pass
                        # Pace per-symbol to avoid flooding
                        time.sleep(max(0.005, 1.0 / (self._ws_speed * max(1, len(symbols)))))
        finally:
            if callable(self._ws_on_close):
                try:
                    self._ws_on_close(None, None, "closed")
                except Exception:
                    pass

    def symbols_to_subscribe(self, symbols: List[str]) -> None:  # type: ignore[override]
        # Accept EXCH:SYMBOL strings
        self._ws_symbols = [s for s in symbols if isinstance(s, str)]

    def connect_order_websocket(self, **kwargs: Any) -> None:  # type: ignore[override]
        # Store callback for synthetic events from place/cancel
        cb = kwargs.get("on_order_update")
        if callable(cb):
            setattr(self, "_on_order_update_cb", cb)

    def unsubscribe(self, symbols: List[str]) -> None:  # type: ignore[override]
        remove = set(symbols)
        self._ws_symbols = [s for s in self._ws_symbols if s not in remove]

    # --- Margins ---
    def get_margins_required(self, orders: List[Dict[str, Any]]) -> Any:
        # Proxy to Fyers multiorder margin if available; otherwise simple heuristic
        try:
            if getattr(self, "_seed_fyers", None):
                return self._seed_fyers.get_margins_required(orders)
        except Exception:
            pass
        # Heuristic: 10% of notional
        total = 0.0
        for o in orders:
            sym = o.get("symbol")
            qty = int(o.get("qty") or o.get("quantity") or 1)
            px = float(o.get("limitPrice") or 0.0) or self._seed_quote(sym)
            total += px * qty * 0.1
        return {"code": 200, "s": "ok", "data": {"margin_total": total, "margin_new_order": total, "margin_avail": 1_000_000 - total}}

    def get_span_margin(self, orders: List[Dict[str, Any]]) -> Any:
        # Try Fyers span margin; fallback to multiorder
        try:
            if getattr(self, "_seed_fyers", None):
                try:
                    return self._seed_fyers.get_span_margin(orders)
                except Exception:
                    return self._seed_fyers.get_margins_required(orders)
        except Exception as e:
            raise MarginUnavailableError(str(e))
        return self.get_margins_required(orders)

    def get_multiorder_margin(self, orders: List[Dict[str, Any]]) -> Any:
        return self.get_margins_required(orders)

    # --- Positions utils ---
    def exit_positions(self, *args: Any, **kwargs: Any) -> Any:
        self._positions.clear()
        return {"s": "ok"}

    def convert_position(self, *args: Any, **kwargs: Any) -> Any:
        return {"s": "ok"}


