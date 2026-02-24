"""
Stock Chart Component
=====================

Renders interactive stock price charts using Plotly.
"""

import streamlit as st

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from models.stock import StockSnapshot


def render_stock_chart(
    snapshots: List["StockSnapshot"],
    ticker: str,
    show_sma: bool = True,
) -> None:
    """
    Render an interactive stock price chart.

    Args:
        snapshots: List of StockSnapshot objects (sorted by date)
        ticker: Ticker symbol for the chart title
        show_sma: Whether to show SMA overlays
    """
    if not HAS_PLOTLY:
        st.warning("Install plotly for stock charts: pip install plotly")
        return

    if not snapshots:
        st.info(f"No stock data available for {ticker}.")
        return

    dates = [s.date for s in snapshots]
    closes = [s.close for s in snapshots]

    fig = go.Figure()

    # Close price line
    fig.add_trace(go.Scatter(
        x=dates,
        y=closes,
        mode="lines",
        name="Close",
        line=dict(color="#4A90D9", width=2),
    ))

    # SMA-20 overlay
    if show_sma:
        sma_20 = [s.sma_20 for s in snapshots]
        if any(v is not None for v in sma_20):
            fig.add_trace(go.Scatter(
                x=dates,
                y=sma_20,
                mode="lines",
                name="SMA-20",
                line=dict(color="#FF8C00", width=1, dash="dash"),
            ))

        # SMA-50 overlay
        sma_50 = [s.sma_50 for s in snapshots]
        if any(v is not None for v in sma_50):
            fig.add_trace(go.Scatter(
                x=dates,
                y=sma_50,
                mode="lines",
                name="SMA-50",
                line=dict(color="#888888", width=1, dash="dot"),
            ))

    fig.update_layout(
        title=f"{ticker} Stock Price",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_white",
        height=400,
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_stock_summary(snapshot: "StockSnapshot", company_info: dict = None) -> None:
    """Render a summary card for a single stock."""
    cols = st.columns(4)

    with cols[0]:
        st.metric(
            label="Close",
            value=f"${snapshot.close:.2f}" if snapshot.close else "N/A",
            delta=f"{snapshot.change_percent:+.2f}%" if snapshot.change_percent else None,
        )
    with cols[1]:
        st.metric(
            label="Volume",
            value=f"{snapshot.volume:,.0f}" if snapshot.volume else "N/A",
        )
    with cols[2]:
        st.metric(
            label="SMA-20",
            value=f"${snapshot.sma_20:.2f}" if snapshot.sma_20 else "N/A",
        )
    with cols[3]:
        st.metric(
            label="SMA-50",
            value=f"${snapshot.sma_50:.2f}" if snapshot.sma_50 else "N/A",
        )

    if company_info:
        st.caption(f"**{company_info.get('company', '')}** — {company_info.get('focus', '')}")
