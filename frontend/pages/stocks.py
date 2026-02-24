"""
Stocks Page
===========

Quantum computing stock dashboard with overview table and per-ticker charts.
"""

import asyncio
import streamlit as st

from config.tickers import (
    PURE_PLAY_TICKERS, MAJOR_TECH_TICKERS, ETF_TICKERS, ALL_TICKERS,
)


def render_stocks_page() -> None:
    """Render the stocks dashboard page."""
    st.header("Quantum Stock Dashboard")

    from storage import get_storage
    storage = get_storage()

    # Fetch latest stock data
    latest_data = asyncio.run(storage.get_latest_stock_data(ALL_TICKERS))

    if not latest_data:
        st.info(
            "No stock data available. Run ingestion with stocks:\n\n"
            "```\npython scripts/run_ingestion.py --sources stocks\n```"
        )
        return

    # Build lookup
    ticker_latest = {s.ticker: s for s in latest_data}

    # Build ticker info lookup
    ticker_info = {}
    for group in [PURE_PLAY_TICKERS, MAJOR_TECH_TICKERS, ETF_TICKERS]:
        for entry in group:
            ticker_info[entry["ticker"]] = entry

    # Overview table
    st.subheader("Market Overview")

    table_data = []
    for ticker in ALL_TICKERS:
        snap = ticker_latest.get(ticker)
        info = ticker_info.get(ticker, {})
        if snap:
            table_data.append({
                "Ticker": ticker,
                "Company": info.get("company", ""),
                "Close": f"${snap.close:.2f}" if snap.close else "N/A",
                "Change %": f"{snap.change_percent:+.2f}%" if snap.change_percent else "N/A",
                "Volume": f"{snap.volume:,.0f}" if snap.volume else "N/A",
                "SMA-20": f"${snap.sma_20:.2f}" if snap.sma_20 else "N/A",
                "SMA-50": f"${snap.sma_50:.2f}" if snap.sma_50 else "N/A",
                "Date": snap.date,
            })

    if table_data:
        st.dataframe(table_data, use_container_width=True, hide_index=True)

    st.divider()

    # Per-ticker detail view
    st.subheader("Ticker Detail")

    available_tickers = [t for t in ALL_TICKERS if t in ticker_latest]
    if not available_tickers:
        return

    selected = st.selectbox("Select Ticker", available_tickers)

    if selected:
        days = st.slider("History (days)", 7, 90, 30)
        snapshots = asyncio.run(storage.get_stock_data(selected, days=days))

        if snapshots:
            info = ticker_info.get(selected, {})

            # Company info
            if info:
                st.markdown(f"**{info.get('company', selected)}** — {info.get('focus', '')}")

            # Storage returns DESC order (newest first) — reverse for charts
            snapshots_asc = list(reversed(snapshots))

            # Summary metrics (latest = first in DESC order)
            from frontend.components.stock_chart import render_stock_summary, render_stock_chart
            render_stock_summary(snapshots[0], info)

            # Price chart (needs ascending order)
            render_stock_chart(snapshots_asc, selected)
        else:
            st.info(f"No historical data for {selected}.")
