from __future__ import annotations

import pandas as pd
import streamlit as st

from charts import comparison_chart, price_chart
from database import get_assets
from market_data import fetch_many_market_data
from utils.formatting import format_percent
from utils.ui import bootstrap_page


bootstrap_page("Markets")

assets = get_assets(active_only=True)
if assets.empty:
    st.info("Add tickers in Settings to track markets.")
    st.stop()

st.subheader("Configurable Revolut watchlist")
st.dataframe(assets, use_container_width=True, hide_index=True)

tickers = assets["ticker"].tolist()
default_selection = tickers[: min(4, len(tickers))]
selected = st.multiselect("Tickers to analyze", tickers, default=default_selection)
force = st.button("Refresh selected market data")

if not selected:
    st.info("Select at least one ticker.")
    st.stop()

market = fetch_many_market_data(selected, force_refresh=force)
rows = []
for ticker, data in market.items():
    rows.append(
        {
            "Ticker": ticker,
            "Price": data.get("price"),
            "1 day": data.get("change_1d"),
            "1 month": data.get("perf_1m"),
            "3 months": data.get("perf_3m"),
            "6 months": data.get("perf_6m"),
            "1 year": data.get("perf_1y"),
            "MM50": data.get("ma50"),
            "MM200": data.get("ma200"),
            "RSI14": data.get("rsi14"),
            "Volatility": data.get("volatility"),
            "Average volume": data.get("avg_volume"),
            "Status": data.get("status"),
            "Error": data.get("error"),
        }
    )

metrics = pd.DataFrame(rows)
for col in ["1 day", "1 month", "3 months", "6 months", "1 year", "Volatility"]:
    if col in metrics:
        metrics[col] = metrics[col].map(format_percent)
st.subheader("Indicators")
st.dataframe(metrics, use_container_width=True, hide_index=True)

selected_chart = st.selectbox("Price chart", selected)
st.plotly_chart(price_chart(market[selected_chart].get("history", []), selected_chart), use_container_width=True)

st.plotly_chart(
    comparison_chart({ticker: data.get("history", []) for ticker, data in market.items()}),
    use_container_width=True,
)
