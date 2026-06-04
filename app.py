from __future__ import annotations

import streamlit as st

from charts import allocation_gap_bar, allocation_pie
from database import load_settings, seed_demo_portfolio
from market_data import check_price_alerts
from risk_management import generate_risk_alerts
from strategy import build_monthly_plan, generate_recommendations
from utils.formatting import format_currency
from utils.i18n import current_language
from utils.onboarding import show_onboarding_if_needed
from utils.ui import bootstrap_page, investment_ideas_frame, metrics_row, render_alerts

bootstrap_page("Dashboard")
settings = load_settings()
lang = current_language(settings)
show_onboarding_if_needed(settings)

txt = {
    "quick_actions": "Quick actions" if lang == "en" else "Actions rapides",
    "refresh_data": "Refresh market data" if lang == "en" else "Actualiser les donnees de marche",
    "load_demo_if_empty": "Load sample portfolio if empty" if lang == "en" else "Charger le portefeuille fictif si vide",
    "demo_loaded": "Sample data loaded if portfolio was empty." if lang == "en" else "Donnees fictives chargees si le portefeuille etait vide.",
    "price_alerts_count": "{n} price alert(s) triggered" if lang == "en" else "🔔 {n} alertes de prix déclenchées",
    "manage_alerts": "Manage my alerts" if lang == "en" else "Gérer mes alertes",
    "monthly_plan": "Indicative monthly plan" if lang == "en" else "Plan mensuel indicatif",
    "budget": "Budget" if lang == "en" else "Enveloppe",
    "stocks": "Stocks" if lang == "en" else "Actions",
    "cash": "Cash" if lang == "en" else "Cash",
    "risk_alerts": "Risk alerts" if lang == "en" else "Alertes de risque",
    "top_etf": "Top 5 ETF ideas to review" if lang == "en" else "5 meilleures idées ETF à analyser",
    "top_stocks": "Top 5 stock ideas to monitor" if lang == "en" else "5 meilleures actions à surveiller",
    "target": "target" if lang == "en" else "cible",
}

with st.sidebar:
    st.subheader(txt["quick_actions"])
    force_refresh = st.button(txt["refresh_data"])
    if st.button(txt["load_demo_if_empty"]):
        seed_demo_portfolio(overwrite=False)
        st.success(txt["demo_loaded"])
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
    st.warning(txt["price_alerts_count"].format(n=len(triggered_price_alerts)))
    with st.expander(txt["manage_alerts"]):
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
    st.write(f"**{bucket}** : {current:.0%} / {txt['target']} {target:.0%}")
    st.progress(min(max(current, 0.0), 1.0))

st.subheader(txt["monthly_plan"])
col1, col2, col3, col4 = st.columns(4)
currency = summary["currency"]
col1.metric(txt["budget"], format_currency(plan["monthly_amount"], currency))
col2.metric("ETF", format_currency(plan["bucket_amounts"]["ETF"], currency))
col3.metric(txt["stocks"], format_currency(plan["bucket_amounts"]["ACTION"], currency))
col4.metric(txt["cash"], format_currency(plan["bucket_amounts"]["CASH"], currency))

if plan["warnings"]:
    for warning in plan["warnings"]:
        st.warning(warning)

st.subheader(txt["risk_alerts"])
render_alerts(alerts)

st.subheader(txt["top_etf"])
st.dataframe(investment_ideas_frame([r for r in recommendations if r["asset_type"] == "ETF"][:5]), use_container_width=True, hide_index=True)

st.subheader(txt["top_stocks"])
st.dataframe(investment_ideas_frame([r for r in recommendations if r["asset_type"] == "ACTION"][:5]), use_container_width=True, hide_index=True)
