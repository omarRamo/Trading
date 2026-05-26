from __future__ import annotations

import streamlit as st

from charts import allocation_gap_bar, allocation_pie
from database import load_settings, seed_demo_portfolio
from market_data import check_price_alerts
from risk_management import generate_risk_alerts
from strategy import build_monthly_plan, generate_recommendations
from utils.formatting import format_currency
from utils.onboarding import show_onboarding_if_needed
from utils.ui import bootstrap_page, investment_ideas_frame, metrics_row, render_alerts

bootstrap_page("Dashboard")
settings = load_settings()
show_onboarding_if_needed(settings)

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
triggered_price_alerts = check_price_alerts(summary.get("user_id", "local_legacy"), summary.get("market_by_ticker", {}))
if triggered_price_alerts:
    st.warning(f"🔔 {len(triggered_price_alerts)} alertes de prix déclenchées")
    with st.expander("Gérer mes alertes"):
        st.dataframe(triggered_price_alerts, use_container_width=True, hide_index=True)

metrics_row(summary, monthly_available=float(settings.get("monthly_investment", 1000)))
st.caption(summary["currency_note"])

left, right = st.columns([1, 1])
with left:
    st.plotly_chart(allocation_pie(summary["allocation_current"], "Allocation actuelle"), use_container_width=True)
with right:
    st.plotly_chart(allocation_gap_bar(summary["allocation_current"], summary["allocation_target"]), use_container_width=True)

for bucket, target in summary["allocation_target"].items():
    current = summary["allocation_current"].get(bucket, 0.0)
    st.write(f"**{bucket}** : {current:.0%} / cible {target:.0%}")
    st.progress(min(max(current, 0.0), 1.0))

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
st.dataframe(investment_ideas_frame([r for r in recommendations if r["asset_type"] == "ETF"][:5]), use_container_width=True, hide_index=True)

st.subheader("5 meilleures actions à surveiller")
st.dataframe(investment_ideas_frame([r for r in recommendations if r["asset_type"] == "ACTION"][:5]), use_container_width=True, hide_index=True)
