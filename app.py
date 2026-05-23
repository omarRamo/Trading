from __future__ import annotations

import pandas as pd
import streamlit as st

from charts import allocation_gap_bar, allocation_pie
from database import load_settings, seed_demo_portfolio
from portfolio import compute_portfolio_summary
from risk_management import generate_risk_alerts
from strategy import build_monthly_plan, generate_recommendations
from utils.formatting import format_currency, format_percent
from utils.ui import bootstrap_page, investment_ideas_frame, metrics_row, render_alerts


bootstrap_page("Dashboard")

settings = load_settings()

with st.sidebar:
    st.subheader("Actions rapides")
    force_refresh = st.button("Actualiser les donnees de marche")
    if st.button("Charger le portefeuille fictif si vide"):
        seed_demo_portfolio(overwrite=False)
        st.success("Donnees fictives chargees si le portefeuille etait vide.")
        st.rerun()

recommendations, summary = generate_recommendations(force_market_refresh=force_refresh)
plan = build_monthly_plan(
    monthly_amount=float(settings.get("monthly_investment", 1000)),
    recommendations=recommendations,
    summary=summary,
    settings=settings,
)
alerts = generate_risk_alerts(summary, settings)

metrics_row(summary)
st.caption(summary["currency_note"])

left, right = st.columns([1, 1])
with left:
    st.plotly_chart(allocation_pie(summary["allocation_current"], "Allocation actuelle"), use_container_width=True)
with right:
    st.plotly_chart(allocation_gap_bar(summary["allocation_current"], summary["allocation_target"]), use_container_width=True)

st.subheader("Plan mensuel indicatif")
col1, col2, col3, col4 = st.columns(4)
currency = summary["currency"]
col1.metric("Enveloppe", format_currency(plan["monthly_amount"], currency))
col2.metric("ETF", format_currency(plan["bucket_amounts"]["ETF"], currency))
col3.metric("Actions", format_currency(plan["bucket_amounts"]["ACTION"], currency))
col4.metric("Cash", format_currency(plan["bucket_amounts"]["CASH"], currency))

if plan["warnings"]:
    for warning in plan["warnings"]:
        st.warning(warning)

st.subheader("Alertes de risque")
render_alerts(alerts)

st.subheader("5 meilleures idées ETF à analyser")
etf_recs = [rec for rec in recommendations if rec["asset_type"] == "ETF"][:5]
st.dataframe(investment_ideas_frame(etf_recs), use_container_width=True, hide_index=True)

st.subheader("5 meilleures actions à surveiller")
stock_recs = [rec for rec in recommendations if rec["asset_type"] == "ACTION"][:5]
st.dataframe(investment_ideas_frame(stock_recs), use_container_width=True, hide_index=True)

st.subheader("Positions")
positions = summary["positions"]
if positions.empty:
    st.info("Aucune position enregistree. Va dans Portefeuille ou Parametres pour charger l'exemple fictif.")
else:
    display = positions[
        [
            "ticker",
            "name",
            "asset_type",
            "quantity",
            "avg_buy_price",
            "current_price",
            "current_value",
            "weight",
            "unrealized_pnl",
            "market_status",
        ]
    ].copy()
    display["weight"] = display["weight"].map(format_percent)
    st.dataframe(display, use_container_width=True, hide_index=True)
