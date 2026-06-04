from __future__ import annotations

import streamlit as st

from utils.ui import bootstrap_page


bootstrap_page("Wiki")

st.info(
    "This page explains the app concepts. It is educational and not financial advice."
)

st.subheader("Dashboard")
st.write(
    "Dashboard combines portfolio value, cash, current allocation, "
    "target allocation, alerts, and top candidates to review."
)

st.subheader("Portfolio")
st.write(
    "Portfolio is entered manually. It is used to compute weights, unrealized P/L, "
    "allocation gaps, and concentration limits. Local deletion does not modify Revolut."
)

st.subheader("Markets")
st.write(
    "Markets page fetches prices via yfinance and computes recent performance, MA50, MA200, RSI, "
    "volatility, and average volume. If one ticker fails, others keep working."
)

st.subheader("Monthly plan")
st.write(
    "Monthly plan transforms your budget into an indicative allocation. It increases underweight buckets, "
    "rebuilds cash when needed, and blocks over-concentrated stocks."
)

st.subheader("Investment ideas")
st.write(
    "Ideas are candidates to review. The score goes from 0 to 100 and signals stay simple: "
    "interesting, watch, wait, avoid. Final decision remains manual."
)

st.subheader("Backtest")
st.write(
    "Backtest compares simple historical scenarios: ETF DCA, 70/20/10 allocation, and one-time initial buy. "
    "It ignores taxes, detailed fees, FX conversion, and exact Revolut availability."
)

st.subheader("RSI, MM50, MM200")
st.write(
    "RSI highlights potential overbought/weakness conditions. MA50 and MA200 are moving averages: "
    "they help visualize trend, without predicting the future."
)

st.subheader("Risque et concentration")
st.write(
    "Individual stocks are capped between 5% and 10% depending on your settings. ETFs may have higher weights, "
    "but the app flags sector concentration and high correlations."
)

st.subheader("User profiles")
st.write(
    "Each account creates a distinct local profile in SQLite. Data is isolated between users."
)
