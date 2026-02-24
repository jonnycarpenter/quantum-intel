"""
Test Stock Fetcher
==================

Tests for the StockFetcher with mocked yfinance.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timezone

import pandas as pd
import numpy as np

from fetchers.stocks import StockFetcher
from models.stock import StockSnapshot


def make_mock_dataframe(tickers=None, days=10):
    """Create a mock multi-ticker DataFrame similar to yf.download output."""
    if tickers is None:
        tickers = ["IONQ", "QBTS"]

    dates = pd.date_range(end="2025-02-15", periods=days, freq="B")

    if len(tickers) > 1:
        # Multi-ticker: MultiIndex columns (ticker, OHLCV)
        data = {}
        for ticker in tickers:
            base = 10 + hash(ticker) % 20
            for col in ["Open", "High", "Low", "Close", "Volume"]:
                if col == "Volume":
                    data[(ticker, col)] = [1000000 + i * 10000 for i in range(days)]
                elif col == "High":
                    data[(ticker, col)] = [base + 1 + i * 0.1 for i in range(days)]
                elif col == "Low":
                    data[(ticker, col)] = [base - 1 + i * 0.1 for i in range(days)]
                elif col == "Open":
                    data[(ticker, col)] = [base + i * 0.1 for i in range(days)]
                else:  # Close
                    data[(ticker, col)] = [base + 0.5 + i * 0.1 for i in range(days)]

        columns = pd.MultiIndex.from_tuples(data.keys())
        df = pd.DataFrame(data, index=dates, columns=columns)
    else:
        # Single ticker: flat columns
        base = 10
        data = {
            "Open": [base + i * 0.1 for i in range(days)],
            "High": [base + 1 + i * 0.1 for i in range(days)],
            "Low": [base - 1 + i * 0.1 for i in range(days)],
            "Close": [base + 0.5 + i * 0.1 for i in range(days)],
            "Volume": [1000000 + i * 10000 for i in range(days)],
        }
        df = pd.DataFrame(data, index=dates)

    return df


@pytest.mark.asyncio
@patch("fetchers.stocks.yf")
async def test_fetch_all_basic(mock_yf):
    """Test basic stock fetching with mocked yfinance."""
    mock_df = make_mock_dataframe(tickers=["IONQ", "QBTS"], days=10)
    mock_yf.download.return_value = mock_df

    # Mock market cap lookup
    mock_ticker = MagicMock()
    mock_ticker.info = {"marketCap": 5000000000}
    mock_yf.Ticker.return_value = mock_ticker

    fetcher = StockFetcher()
    fetcher.tickers = ["IONQ", "QBTS"]

    snapshots = await fetcher.fetch_all(days_back=10)

    assert len(snapshots) > 0
    tickers_in_results = {s.ticker for s in snapshots}
    assert "IONQ" in tickers_in_results or "QBTS" in tickers_in_results


@pytest.mark.asyncio
@patch("fetchers.stocks.yf")
async def test_fetch_all_empty_response(mock_yf):
    """Test handling of empty DataFrame."""
    mock_yf.download.return_value = pd.DataFrame()

    fetcher = StockFetcher()
    fetcher.tickers = ["IONQ"]

    snapshots = await fetcher.fetch_all(days_back=5)
    assert len(snapshots) == 0


@pytest.mark.asyncio
@patch("fetchers.stocks.yf")
async def test_fetch_all_download_failure(mock_yf):
    """Test handling of yfinance download failure."""
    mock_yf.download.side_effect = Exception("Network error")

    fetcher = StockFetcher()
    fetcher.tickers = ["IONQ"]

    snapshots = await fetcher.fetch_all(days_back=5)
    assert len(snapshots) == 0


def test_process_ticker():
    """Test processing a single ticker's data."""
    df = make_mock_dataframe(tickers=["IONQ", "QBTS"], days=25)

    fetcher = StockFetcher()
    fetcher.tickers = ["IONQ", "QBTS"]
    fetcher._market_cap_cache = {"IONQ": 5000000000, "QBTS": 2000000000}

    snapshots = fetcher._process_ticker(df, "IONQ")

    assert len(snapshots) == 25
    assert all(s.ticker == "IONQ" for s in snapshots)
    assert all(s.date is not None for s in snapshots)
    assert all(s.close is not None for s in snapshots)

    # SMA-20 should be calculated (after 20 data points, exact; before that, partial)
    assert snapshots[-1].sma_20 is not None


def test_process_ticker_missing():
    """Test processing when ticker has no data."""
    df = make_mock_dataframe(tickers=["IONQ", "QBTS"], days=5)

    fetcher = StockFetcher()
    fetcher.tickers = ["IONQ", "QBTS"]
    fetcher._market_cap_cache = {}

    # Try to get data for a ticker that's not in the DataFrame
    snapshots = fetcher._process_ticker(df, "NONEXISTENT")
    assert len(snapshots) == 0


def test_stock_snapshot_change_percent():
    """Test that change_percent is calculated."""
    df = make_mock_dataframe(tickers=["IONQ", "QBTS"], days=5)

    fetcher = StockFetcher()
    fetcher.tickers = ["IONQ", "QBTS"]
    fetcher._market_cap_cache = {"IONQ": None}

    snapshots = fetcher._process_ticker(df, "IONQ")

    # First day's change_percent should be None (no previous close)
    assert snapshots[0].change_percent is None
    # Subsequent days should have a change_percent
    assert snapshots[1].change_percent is not None
