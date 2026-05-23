from __future__ import annotations

import pandas as pd
import streamlit as st

from charts import comparison_chart, price_chart
from database import get_assets
from market_data import fetch_many_market_data
from utils.formatting import format_percent
from utils.ui import bootstrap_page


bootstrap_page("Marches")

assets = get_assets(active_only=True)
if assets.empty:
    st.info("Ajoute des tickers dans Parametres pour suivre les marches.")
    st.stop()

st.subheader("Watchlist Revolut configurable")
st.dataframe(assets, use_container_width=True, hide_index=True)

tickers = assets["ticker"].tolist()
default_selection = tickers[: min(4, len(tickers))]
selected = st.multiselect("Tickers a analyser", tickers, default=default_selection)
force = st.button("Rafraichir les donnees selectionnees")

if not selected:
    st.info("Selectionne au moins un ticker.")
    st.stop()

market = fetch_many_market_data(selected, force_refresh=force)
rows = []
for ticker, data in market.items():
    rows.append(
        {
            "Ticker": ticker,
            "Prix": data.get("price"),
            "1 jour": data.get("change_1d"),
            "1 mois": data.get("perf_1m"),
            "3 mois": data.get("perf_3m"),
            "6 mois": data.get("perf_6m"),
            "1 an": data.get("perf_1y"),
            "MM50": data.get("ma50"),
            "MM200": data.get("ma200"),
            "RSI14": data.get("rsi14"),
            "Volatilite": data.get("volatility"),
            "Volume moyen": data.get("avg_volume"),
            "Statut": data.get("status"),
            "Erreur": data.get("error"),
        }
    )

metrics = pd.DataFrame(rows)
for col in ["1 jour", "1 mois", "3 mois", "6 mois", "1 an", "Volatilite"]:
    if col in metrics:
        metrics[col] = metrics[col].map(format_percent)
st.subheader("Indicateurs")
st.dataframe(metrics, use_container_width=True, hide_index=True)

selected_chart = st.selectbox("Courbe de prix", selected)
st.plotly_chart(price_chart(market[selected_chart].get("history", []), selected_chart), use_container_width=True)

st.plotly_chart(
    comparison_chart({ticker: data.get("history", []) for ticker, data in market.items()}),
    use_container_width=True,
)
