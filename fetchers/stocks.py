"""
Stock Data Fetcher
==================

Fetches stock market data for quantum computing companies using yfinance.
Produces StockSnapshot objects for direct storage (not the article pipeline).
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import yfinance as yf

from config.settings import IngestionConfig
from config.tickers import ALL_TICKERS, PURE_PLAY_TICKERS, MAJOR_TECH_TICKERS, ETF_TICKERS
from models.stock import StockSnapshot
from utils.logger import get_logger

logger = get_logger(__name__)


class StockFetcher:
    """
    Fetches stock data for quantum computing companies.

    Features:
    - Batch download for all 15 public tickers via yfinance
    - Derived metrics: change_percent, SMA-20, SMA-50
    - Market cap lookup (cached per ticker)
    - Separate pipeline — produces StockSnapshot, not RawArticle
    """

    def __init__(self, config: Optional[IngestionConfig] = None):
        self.config = config
        self.tickers = ALL_TICKERS
        self._market_cap_cache: Dict[str, Optional[float]] = {}

    async def fetch_all(self, days_back: int = 60) -> List[StockSnapshot]:
        """
        Fetch historical stock data for all tracked tickers.

        Args:
            days_back: Number of days of historical data to fetch

        Returns:
            List of StockSnapshot objects across all tickers and dates
        """
        period = f"{days_back}d"
        logger.info(f"[FETCHER] Stocks: fetching {len(self.tickers)} tickers ({period})")

        # yfinance is synchronous — run in executor
        loop = asyncio.get_event_loop()

        try:
            df = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    tickers=self.tickers,
                    period=period,
                    group_by="ticker",
                    progress=False,
                    threads=True,
                ),
            )
        except Exception as e:
            logger.error(f"[FETCHER] Stocks batch download failed: {e}")
            return []

        if df is None or df.empty:
            logger.warning("[FETCHER] Stocks: empty response from yfinance")
            return []

        # Fetch market caps
        await self._fetch_market_caps()

        all_snapshots: List[StockSnapshot] = []

        for ticker in self.tickers:
            try:
                snapshots = self._process_ticker(df, ticker)
                all_snapshots.extend(snapshots)
            except Exception as e:
                logger.warning(f"[FETCHER] Stocks: error processing {ticker}: {e}")

        logger.info(
            f"[FETCHER] Stocks total: {len(all_snapshots)} snapshots "
            f"for {len(self.tickers)} tickers"
        )
        return all_snapshots

    async def fetch_latest(self) -> List[StockSnapshot]:
        """
        Fetch only the most recent day's data for all tickers.

        Returns:
            List with one StockSnapshot per ticker (latest trading day)
        """
        logger.info(f"[FETCHER] Stocks: fetching latest for {len(self.tickers)} tickers")

        loop = asyncio.get_event_loop()

        try:
            # Use 5d to ensure we get at least one trading day
            df = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    tickers=self.tickers,
                    period="5d",
                    group_by="ticker",
                    progress=False,
                    threads=True,
                ),
            )
        except Exception as e:
            logger.error(f"[FETCHER] Stocks latest download failed: {e}")
            return []

        if df is None or df.empty:
            logger.warning("[FETCHER] Stocks: empty response from yfinance")
            return []

        await self._fetch_market_caps()

        latest_snapshots: List[StockSnapshot] = []

        for ticker in self.tickers:
            try:
                snapshots = self._process_ticker(df, ticker)
                if snapshots:
                    # Take only the latest
                    latest_snapshots.append(snapshots[-1])
            except Exception as e:
                logger.warning(f"[FETCHER] Stocks: error getting latest {ticker}: {e}")

        logger.info(f"[FETCHER] Stocks latest: {len(latest_snapshots)} tickers")
        return latest_snapshots

    def _process_ticker(self, df: Any, ticker: str) -> List[StockSnapshot]:
        """
        Process a single ticker's data from the batch download DataFrame.

        Args:
            df: pandas DataFrame from yf.download (multi-ticker, grouped by ticker)
            ticker: Stock ticker symbol

        Returns:
            List of StockSnapshot objects for this ticker
        """
        try:
            # Multi-ticker DataFrame: columns are (ticker, OHLCV)
            if len(self.tickers) > 1:
                ticker_df = df[ticker].dropna(how="all")
            else:
                ticker_df = df.dropna(how="all")
        except (KeyError, TypeError):
            logger.debug(f"[FETCHER] Stocks: no data for {ticker}")
            return []

        if ticker_df.empty:
            return []

        # Calculate derived metrics
        close_series = ticker_df["Close"]
        sma_20 = close_series.rolling(window=20, min_periods=1).mean()
        sma_50 = close_series.rolling(window=50, min_periods=1).mean()
        change_pct = close_series.pct_change() * 100

        market_cap = self._market_cap_cache.get(ticker)

        snapshots = []
        for idx, row in ticker_df.iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]

            snapshot = StockSnapshot.from_yfinance_row(
                ticker=ticker,
                date_str=date_str,
                row={
                    "Open": row.get("Open"),
                    "High": row.get("High"),
                    "Low": row.get("Low"),
                    "Close": row.get("Close"),
                    "Volume": row.get("Volume"),
                },
                market_cap=market_cap,
                sma_20=sma_20.get(idx),
                sma_50=sma_50.get(idx),
                change_percent=change_pct.get(idx),
            )
            snapshots.append(snapshot)

        return snapshots

    async def _fetch_market_caps(self) -> None:
        """Fetch market caps for all tickers (cached)."""
        if self._market_cap_cache:
            return  # Already fetched this session

        loop = asyncio.get_event_loop()

        for ticker in self.tickers:
            try:
                info = await loop.run_in_executor(
                    None,
                    lambda t=ticker: yf.Ticker(t).info,
                )
                self._market_cap_cache[ticker] = info.get("marketCap")
            except Exception:
                self._market_cap_cache[ticker] = None
                logger.debug(f"[FETCHER] Stocks: could not get market cap for {ticker}")
