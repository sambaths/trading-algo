import logging
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, Any, Optional, List
import requests
import hashlib, pyotp
from dotenv import load_dotenv
from brokers_old.base import BrokerBase
from kiteconnect import KiteConnect, KiteTicker
import pandas as pd
from threading import Thread

from logger import logger


load_dotenv()


# --- Zerodha Broker ---
class ZerodhaBroker(BrokerBase):
    def __init__(self, without_totp):
        super().__init__()
        self.without_totp = without_totp
        self.kite, self.auth_response_data = self.authenticate()
        # self.kite.set_access_token(self.auth_response_data["access_token"])
        self.kite_ws = KiteTicker(api_key=os.getenv('BROKER_API_KEY'), access_token=self.auth_response_data["access_token"])
        self.tick_counter = 0
        self.symbols = []
        
    def authenticate(self):
        api_key = os.getenv('BROKER_API_KEY')
        api_secret = os.getenv('BROKER_API_SECRET')
        broker_id = os.getenv('BROKER_ID')
        totp_secret = os.getenv('BROKER_TOTP_KEY')
        password = os.getenv('BROKER_PASSWORD')

        if self.without_totp:
            kite = KiteConnect(api_key=os.getenv('BROKER_API_KEY'))
            print(f"Please Login to Zerodha and get the request token from the URL.\n {kite.login_url()} \nThen paste the request token here:")
            request_token = input("Request Token: ")
            resp = kite.generate_session(request_token, os.environ['BROKER_API_SECRET'])
            return kite, resp
        

        if not all([api_key, api_secret, broker_id, totp_secret]):
            raise Exception("Missing one or more required environment variables.")

        session = requests.Session()

        # Step 1: Login 
        login_url = "https://kite.zerodha.com/api/login"
        login_payload = {
            "user_id": broker_id,
            "password": password,
        }
        login_resp = session.post(login_url, data=login_payload)
        login_data = login_resp.json()
        if not login_data.get("data"):
            raise Exception(f"Login failed: {login_data}")
        request_id = login_data["data"]["request_id"]

        # Step 2: TwoFA
        twofa_url = "https://kite.zerodha.com/api/twofa"
        twofa_payload = {
            "user_id": broker_id,
            "request_id": request_id,
            "twofa_value": pyotp.TOTP(totp_secret).now(),
            # "twofa_type": "totp",
        }
        twofa_resp = session.post(twofa_url, data=twofa_payload)
        twofa_data = twofa_resp.json()
        if not twofa_data.get("data"):
            raise Exception(f"2FA failed: {twofa_data}")

        kite = KiteConnect(api_key=os.getenv('BROKER_API_KEY'))
        # Step 3: Get request_token from redirect
        connect_url = f"https://kite.trade/connect/login?api_key={api_key}"
        connect_resp = session.get(connect_url, allow_redirects=True)
        if "request_token=" not in connect_resp.url:
            raise Exception("Failed to get request_token from redirect URL.")
        request_token = connect_resp.url.split("request_token=")[1].split("&")[0]

        resp = kite.generate_session(request_token, os.environ['BROKER_API_SECRET'])
        
        return kite, resp
    
    def get_orders(self):
        return self.kite.orders()
    
    def get_quote(self, symbol, exchange):
        if ":" not in symbol:   
            symbol = exchange + ":" + symbol
        return self.kite.quote(symbol)
    
    def place_gtt_order(self, symbol, quantity, price, transaction_type, order_type, exchange, product, tag="Unknown"):
        if order_type not in ["LIMIT", "MARKET"]:
            raise ValueError(f"Invalid order type: {order_type}")
        
        if transaction_type not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid transaction type: {transaction_type}")
        
        order_obj = {
            "exchange": exchange,
            "tradingsymbol": symbol,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "order_type": order_type,
            "product": product,
            "price": price,
            "tag": tag
        }
        last_price = self.get_quote(symbol, exchange)[exchange + ":" + symbol]['last_price']
        order_id = self.kite.place_gtt(trigger_type=self.kite.GTT_TYPE_SINGLE, tradingsymbol=symbol, exchange=exchange, trigger_values=[price], last_price=last_price, orders=order_obj)
        return order_id['trigger_id']
    
    def place_order(self, symbol, quantity, price, transaction_type, order_type, variety, exchange, product, tag="Unknown"):
        if order_type == "LIMIT":
            order_type = self.kite.ORDER_TYPE_LIMIT
        elif order_type == "MARKET":
            order_type = self.kite.ORDER_TYPE_MARKET
        else:
            raise ValueError(f"Invalid order type: {order_type}")
        
        if transaction_type == "BUY":
            transaction_type = self.kite.TRANSACTION_TYPE_BUY
        elif transaction_type == "SELL":
            transaction_type = self.kite.TRANSACTION_TYPE_SELL
        else:
            raise ValueError(f"Invalid transaction type: {transaction_type}")
        
        if variety == "REGULAR":
            variety = self.kite.VARIETY_REGULAR
        else:
            raise ValueError(f"Invalid variety: {variety}")
        
        logger.info(f"Placing order for {symbol} with quantity {quantity} at {price} with order type {order_type} and transaction type {transaction_type}, variety {variety}, exchange {exchange}, product {product}, tag {tag}")
        order_attempt = 0
        try:
            while order_attempt < 5:
                order_id = self.kite.place_order(
                    variety=variety,
                    exchange=exchange,
                    tradingsymbol=symbol,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    product=product,
                    order_type=order_type,
                    price=price if order_type == 'LIMIT' else None,
                    tag=tag
                )
                logger.info(f"Order placed: {order_id}")
                return order_id
            logger.error(f"Order placement failed after 5 attempts")
            return -1
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return -1
    
    def get_quote(self, symbol):
        return self.kite.quote(symbol)
    
    def get_order_status(self, order_id):
        return self.kite.order_history(order_id)

    def get_positions(self):
        return self.kite.positions()

    def symbols_to_subscribe(self, symbols):
        self.symbols = symbols

    ## Websocket Calllbacks
    def on_ticks(self, ws, ticks):  # noqa
        """
        This callback is called when the websocket receives a tick.
        This is the skeleton of the callback.
        The actual implementation has to be handled by the user
        """
        # Callback to receive ticks.
        logger.info("Ticks: {}".format(ticks))
        # self.tick_counter += 1

    def on_connect(self, ws, response):  # noqa
        """
        This callback is called when the websocket is connected.
        This is the skeleton of the callback.
        The actual implementation has to be handled by the user
        """
        # Callback on successful connect.
        # Subscribe to a list of instrument_tokens (RELIANCE and ACC here).
        logger.info("Connected")
        # Set RELIANCE to tick in `full` mode.
        ws.subscribe(self.symbols)
        ws.set_mode(ws.MODE_FULL, self.symbols)


    def on_order_update(self, ws, data):
        """
        This callback is called when the websocket receives an order update.
        This is the skeleton of the callback.
        The actual implementation has to be handled by the user
        """
        logger.info("Order update : {}".format(data))

    def on_close(self, ws, code, reason):
        """
        This callback is called when the websocket is closed.
        This is the skeleton of the callback.
        The actual implementation has to be handled by the user
        """
        logger.info("Connection closed: {code} - {reason}".format(code=code, reason=reason))


    # Callback when connection closed with error.
    def on_error(self, ws, code, reason):
        """
        This callback is called when the websocket encounters an error.
        This is the skeleton of the callback.
        The actual implementation has to be handled by the user
        """
        logger.info("Connection error: {code} - {reason}".format(code=code, reason=reason))


    # Callback when reconnect is on progress
    def on_reconnect(self, ws, attempts_count):
        """
        This callback is called when the websocket is reconnecting.
        This is the skeleton of the callback.
        The actual implementation has to be handled by the user
        """
        logger.info("Reconnecting: {}".format(attempts_count))


    # Callback when all reconnect failed (exhausted max retries)
    def on_noreconnect(self, ws):
        """
        This callback is called when the websocket fails to reconnect.
        This is the skeleton of the callback.
        The actual implementation has to be handled by the user
        """
        logger.info("Reconnect failed.")
    
    def download_instruments(self):
        instruments = self.kite.instruments()
        self.instruments_df = pd.DataFrame(instruments)
    
    def get_instruments(self):
        return self.instruments_df
    
    def connect_websocket(self):
        self.kite_ws.on_ticks = self.on_ticks
        self.kite_ws.on_connect = self.on_connect
        self.kite_ws.on_order_update = self.on_order_update
        self.kite_ws.on_close = self.on_close
        self.kite_ws.on_error = self.on_error
        self.kite_ws.on_reconnect = self.on_reconnect
        self.kite_ws.on_noreconnect = self.on_noreconnect
        self.kite_ws.connect(threaded=True)
        
if __name__ == "__main__":
    broker = ZerodhaBroker(without_totp=False)
    broker.download_instruments()
    df = broker.get_instruments()
    df = df[df['instrument_type'] == 'CE']
    print(df.head().T)