# brokers

broker-agnostic abstraction, It introduces:

- Core domain models and a single driver interface
- Symbol normalization with per-broker resolvers
- Central mapping tables
- Pluggable drivers (`fyers`, `zerodha`) with a registry
- A simple facade `BrokerGateway` for consumers

Example:

```python
from brokers import BrokerGateway, OrderRequest, Exchange, OrderType, TransactionType, ProductType

gw = BrokerGateway.from_name("fyers")  # or "zerodha"
funds = gw.get_funds()  # Raises UnsupportedOperationError until drivers are fully implemented

# Place an order (symbol is canonical EXCH:SYMBOL under the hood)
req = OrderRequest(
    symbol="SBIN",
    exchange=Exchange.NSE,
    quantity=1,
    order_type=OrderType.MARKET,
    transaction_type=TransactionType.BUY,
    product_type=ProductType.CNC,
)
resp = gw.place_order(req)
```

Notes:

- This initial commit scaffolds the architecture. Driver methods raise `UnsupportedOperationError` or `MarginUnavailableError` by design until implemented.
- Symbols are normalized to canonical form `<EXCHANGE>:<TRADINGSYMBOL>`. Resolvers translate to broker-native forms.
- Margins are never estimated locally; drivers must fetch them from broker APIs and raise if unavailable.


