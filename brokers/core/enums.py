from __future__ import annotations

from enum import Enum


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"  # NSE F&O
    BFO = "BFO"  # BSE F&O
    MCX = "MCX"
    CDS = "CDS"  # Currency derivatives


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"  # Stop Market / SL-M
    STOP_LIMIT = "STOP_LIMIT"  # SL


class ProductType(str, Enum):
    INTRADAY = "INTRADAY"  # MIS
    CNC = "CNC"  # Cash & Carry
    MARGIN = "MARGIN"  # NRML / Margin


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Validity(str, Enum):
    DAY = "DAY"
    IOC = "IOC"


class OptionType(str, Enum):
    CE = "CE"
    PE = "PE"


