"""
Stock Snapshot Model
====================

Data model for stock market data in the Quantum Intelligence Hub.
Maps to the `stocks` table in storage/schemas.py.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class StockSnapshot:
    """
    A single day's stock data for a quantum computing company.

    Stored in the `stocks` table with composite PK (ticker, date).
    """

    ticker: str
    date: str  # ISO format date string (YYYY-MM-DD)
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    change_percent: Optional[float] = None
    market_cap: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None

    @classmethod
    def from_yfinance_row(
        cls,
        ticker: str,
        date_str: str,
        row: Dict[str, Any],
        market_cap: Optional[float] = None,
        sma_20: Optional[float] = None,
        sma_50: Optional[float] = None,
        change_percent: Optional[float] = None,
    ) -> "StockSnapshot":
        """
        Create from a yfinance DataFrame row (as dict).

        Args:
            ticker: Stock ticker symbol
            date_str: Date as ISO string (YYYY-MM-DD)
            row: Dict with Open, High, Low, Close, Volume keys
            market_cap: Pre-fetched market cap for this ticker
            sma_20: Pre-calculated 20-day SMA
            sma_50: Pre-calculated 50-day SMA
            change_percent: Pre-calculated daily change percentage
        """
        return cls(
            ticker=ticker,
            date=date_str,
            open=_safe_float(row.get("Open")),
            high=_safe_float(row.get("High")),
            low=_safe_float(row.get("Low")),
            close=_safe_float(row.get("Close")),
            volume=_safe_int(row.get("Volume")),
            change_percent=_safe_float(change_percent),
            market_cap=_safe_float(market_cap),
            sma_20=_safe_float(sma_20),
            sma_50=_safe_float(sma_50),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "ticker": self.ticker,
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "change_percent": self.change_percent,
            "market_cap": self.market_cap,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockSnapshot":
        """Create from dictionary (from storage)."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


def _safe_float(val: Any) -> Optional[float]:
    """Safely convert to float, handling NaN and None."""
    if val is None:
        return None
    try:
        f = float(val)
        # Check for NaN
        if f != f:
            return None
        return round(f, 4)
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    """Safely convert to int, handling NaN and None."""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:
            return None
        return int(f)
    except (TypeError, ValueError):
        return None
