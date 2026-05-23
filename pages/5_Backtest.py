from __future__ import annotations

from datetime import date

import streamlit as st

from backtesting import run_backtest
from charts import backtest_chart
from database import get_assets, load_settings
from utils.formatting import format_percent
from utils.ui import bootstrap_page


bootstrap_page("Backtest")

settings = load_settings()
assets = get_assets(active_only=True)
etf_options = assets.loc[assets["asset_type"] == "ETF", "ticker"].tolist()
stock_options = assets.loc[assets["asset_type"] == "ACTION", "ticker"].tolist()

col1, col2 = st.columns(2)
with col1:
    etfs = st.multiselect("ETF pour la simulation", etf_options, default=etf_options[:1])
    start = st.date_input("Date de debut", value=date(2018, 1, 1))
with col2:
    stocks = st.multiselect("Actions pour la poche 20 %", stock_options, default=stock_options[:3])
    end = st.date_input("Date de fin", value=date.today())

monthly_amount = st.number_input(
    "Investissement mensuel",
    min_value=0.0,
    value=float(settings.get("monthly_investment", 1000)),
    step=50.0,
)

if st.button("Lancer le backtest"):
    result = run_backtest(etfs, stocks, monthly_amount, start.isoformat(), end.isoformat())
    for warning in result.warnings:
        st.warning(warning)
    if result.curve.empty:
        st.stop()

    st.plotly_chart(backtest_chart(result.curve), use_container_width=True)

    metrics = result.metrics.copy()
    for col in ["performance", "cagr", "volatility", "max_drawdown"]:
        metrics[col] = metrics[col].map(format_percent)
    st.subheader("Statistiques")
    st.dataframe(metrics, use_container_width=True, hide_index=True)
    st.caption("Backtest simplifie hors fiscalite, frais, change et disponibilite exacte Revolut.")
else:
    st.info("Simule un DCA mensuel ETF, une repartition 70/20/10 et un achat unique au depart.")
