# trading-algo
Code for certain trading strategies
1. Survivor Algo is Live

## Disclaimer:
This algorithm is provided for **educational** and **informational purposes** only. Trading in financial markets involves substantial risk, and you may lose all or more than your initial investment. By using this algorithm, you acknowledge that all trading decisions are made at your own risk and discretion. The creators of this algorithm assume no liability or responsibility for any financial losses or damages incurred through its use. **Always do your own research and consult with a qualified financial advisor before trading.**


## Setup

### 1. Install Dependencies

To insall uv, use:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
or


```bash
pip install uv
```

This uses `uv` for dependency management. Install dependencies:
```bash
uv sync
```

Or if you prefer using pip:

```bash
pip install -r requirements.txt  # You may need to generate this from pyproject.toml
```

### 2. Environment Configuration

1. Copy the sample environment file:
   ```bash
   cp .sample.env .env
   ```

2. Edit `.env` and fill in your broker credentials:
   ```bash
   # Broker Configuration - Supports Fyers, Zerodha
   BROKER_NAME=fyers  # or zerodha
   BROKER_API_KEY=<YOUR_API_KEY>
   BROKER_API_SECRET=<YOUR_API_SECRET>
   # items below can be skipped if not using TOTP (Fyers currently only has TOTP based login)
   BROKER_TOTP_ENABLE=false # or true
   BROKER_ID=<YOUR_BROKER_ID>
   BROKER_TOTP_REDIDRECT_URI=<YOUR_TOTP_REDIRECT_URI>
   BROKER_TOTP_KEY=<YOUR_TOTP_KEY>
   BROKER_TOTP_PIN=<YOUR_TOTP_PIN>
   BROKER_PASSWORD=<YOUR_BROKER_PASSWORD>  # Required for Zerodha
   ```

### 3. Running Strategies

Strategies should be placed in the `strategy/` folder.

#### Running the Survivor Strategy


**Basic usage (using default config):**
```bash
cd strategy/
python survivor.py
```

**With custom parameters:**
```bash
cd strategy/
python survivor.py \
    --symbol-initials NIFTY25JAN30 \
    --pe-gap 25 --ce-gap 25 \
    --pe-quantity 50 --ce-quantity 50 \
    --min-price-to-sell 15
```

**View current configuration:**
```bash
cd strategy/
python survivor.py --show-config
```

### 4. Available Brokers

- **Fyers**: Supports REST API for historical data, quotes, and WebSocket for live data
- **Zerodha**: Supports KiteConnect API with order management and live data streaming

### 5. Core Components

- `brokers/`: Broker implementations (Fyers, Zerodha)
- `dispatcher.py`: Data routing and queue management
- `orders.py`: Order management utilities
- `logger.py`: Logging configuration
- `strategy/`: Place your trading strategies here

### Example Usage

```python
from brokers.fyers import FyersBroker
from brokers.zerodha import ZerodhaBroker

# Initialize broker based on environment
# ==================
# IMPORTANT - Strategies mentioned here only work with without any code changes, For Fyers - Some Broker level changes 
# is required, for instance - api response for positions, orders etc are different for Zerodha and Brokers
# and would need to handled slighly different.
# Althougth the Strategy Logic would remain unchanged, the places where broker methods are called users would have to
# adapth the code accordingly for now until we are able to standardize the broker classes
# ==================
if os.getenv('BROKER_NAME') == 'fyers':
    broker = FyersBroker(symbols=['NSE:SBIN-EQ'])
    # Fyers is not a stand-in replacement for Zerodha for these strategies
else:
    broker = ZerodhaBroker(without_totp=True) # Only available for Zerodha

# Get historical data, place orders, etc.
```

For more details, check the individual broker implementations and example strategies in the `strategy/` folder.
