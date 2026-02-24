"""
Stock Data Tool
===============

Retrieves stock market data for quantum computing companies.
Wraps SQLite stock queries and provides summary statistics.
"""

import json
import logging
from typing import Optional

from config.tickers import ALL_TICKERS, PURE_PLAY_TICKERS, MAJOR_TECH_TICKERS, ETF_TICKERS

logger = logging.getLogger(__name__)

# Build ticker info lookup
_TICKER_INFO = {}
for group in [PURE_PLAY_TICKERS, MAJOR_TECH_TICKERS, ETF_TICKERS]:
    for entry in group:
        _TICKER_INFO[entry["ticker"]] = {
            "company": entry["company"],
            "focus": entry["focus"],
        }


class StockDataTool:
    """Retrieve stock market data for quantum computing companies."""

    def __init__(self):
        self._storage = None

    def _ensure_initialized(self) -> None:
        """Lazy-initialize storage singleton."""
        if self._storage is None:
            from storage import get_storage
            self._storage = get_storage()

    async def execute(
        self,
        ticker: str,
        days: int = 30,
    ) -> str:
        """
        Get stock data for a ticker and return as JSON string.

        Args:
            ticker: Stock ticker symbol
            days: Number of days of history

        Returns:
            JSON string with stock data and summary
        """
        ticker = ticker.upper().strip()
        logger.info(f"[TOOL] stock_data: ticker={ticker} days={days}")

        # Validate ticker
        if ticker not in ALL_TICKERS:
            return json.dumps({
                "error": f"Unknown ticker: {ticker}",
                "valid_tickers": ALL_TICKERS,
                "message": f"'{ticker}' is not in the tracked quantum computing tickers.",
            })

        self._ensure_initialized()

        try:
            snapshots = await self._storage.get_stock_data(ticker, days=days)
        except Exception as e:
            logger.error(f"[TOOL] stock_data error: {e}")
            return json.dumps({
                "error": f"Failed to fetch stock data: {e}",
                "ticker": ticker,
            })

        if not snapshots:
            return json.dumps({
                "ticker": ticker,
                "company_info": _TICKER_INFO.get(ticker, {}),
                "data": [],
                "message": (
                    f"No stock data available for {ticker}. "
                    "Run ingestion with --sources stocks first."
                ),
            })

        # Storage returns ORDER BY date DESC (newest first)
        latest = snapshots[0]
        oldest = snapshots[-1]

        # Compute period stats
        closes = [s.close for s in snapshots if s.close is not None]
        volumes = [s.volume for s in snapshots if s.volume is not None]

        summary = {
            "latest_date": latest.date,
            "latest_close": latest.close,
            "latest_change_pct": latest.change_percent,
            "sma_20": latest.sma_20,
            "sma_50": latest.sma_50,
            "market_cap": latest.market_cap,
            "period_high": max(closes) if closes else None,
            "period_low": min(closes) if closes else None,
            "avg_volume": int(sum(volumes) / len(volumes)) if volumes else None,
            "period_start": oldest.date,
            "period_days": len(snapshots),
        }

        # Period change
        if latest.close and oldest.close and oldest.close != 0:
            summary["period_change_pct"] = round(
                ((latest.close - oldest.close) / oldest.close) * 100, 2
            )

        # Recent history (last 5 data points for context)
        recent = [
            {
                "date": s.date,
                "close": s.close,
                "volume": s.volume,
                "change_pct": s.change_percent,
            }
            for s in snapshots[-5:]
        ]

        logger.info(f"[TOOL] stock_data: {ticker} — {len(snapshots)} data points")
        return json.dumps({
            "ticker": ticker,
            "company_info": _TICKER_INFO.get(ticker, {}),
            "summary": summary,
            "recent_history": recent,
            "total_data_points": len(snapshots),
        })
