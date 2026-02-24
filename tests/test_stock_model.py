"""
Test Stock Model
================

Tests for the StockSnapshot dataclass.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
from models.stock import StockSnapshot, _safe_float, _safe_int


def test_stock_snapshot_creation():
    """Test creating a StockSnapshot."""
    snap = StockSnapshot(
        ticker="IONQ",
        date="2025-02-15",
        open=12.50,
        high=13.00,
        low=12.25,
        close=12.75,
        volume=1500000,
        change_percent=2.0,
        market_cap=3500000000.0,
        sma_20=12.30,
        sma_50=11.80,
    )
    assert snap.ticker == "IONQ"
    assert snap.date == "2025-02-15"
    assert snap.close == 12.75
    assert snap.volume == 1500000


def test_stock_from_yfinance_row():
    """Test creating StockSnapshot from yfinance data."""
    row = {
        "Open": 12.50,
        "High": 13.00,
        "Low": 12.25,
        "Close": 12.75,
        "Volume": 1500000,
    }

    snap = StockSnapshot.from_yfinance_row(
        ticker="IONQ",
        date_str="2025-02-15",
        row=row,
        market_cap=3500000000.0,
        sma_20=12.30,
        sma_50=11.80,
        change_percent=2.0,
    )
    assert snap.ticker == "IONQ"
    assert snap.open == 12.50
    assert snap.close == 12.75
    assert snap.volume == 1500000
    assert snap.market_cap == 3500000000.0
    assert snap.sma_20 == 12.30
    assert snap.change_percent == 2.0


def test_stock_to_dict_and_back():
    """Test StockSnapshot serialization round-trip."""
    snap = StockSnapshot(
        ticker="QBTS",
        date="2025-02-10",
        open=5.50,
        high=5.80,
        low=5.40,
        close=5.70,
        volume=800000,
        change_percent=1.5,
    )

    d = snap.to_dict()
    assert d["ticker"] == "QBTS"
    assert d["close"] == 5.70

    restored = StockSnapshot.from_dict(d)
    assert restored.ticker == snap.ticker
    assert restored.close == snap.close
    assert restored.volume == snap.volume


def test_safe_float_nan():
    """Test _safe_float handles NaN correctly."""
    assert _safe_float(None) is None
    assert _safe_float(float("nan")) is None
    assert _safe_float(12.5) == 12.5
    assert _safe_float("10.5") == 10.5
    assert _safe_float("not_a_number") is None


def test_safe_int_nan():
    """Test _safe_int handles NaN correctly."""
    assert _safe_int(None) is None
    assert _safe_int(float("nan")) is None
    assert _safe_int(1500000) == 1500000
    assert _safe_int(1500000.7) == 1500000
    assert _safe_int("bad") is None


def test_stock_none_fields():
    """Test StockSnapshot with all optional fields as None."""
    snap = StockSnapshot(ticker="TEST", date="2025-01-01")
    assert snap.open is None
    assert snap.close is None
    assert snap.volume is None
    assert snap.sma_20 is None
    assert snap.market_cap is None
