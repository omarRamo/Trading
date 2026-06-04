from __future__ import annotations

import pandas as pd
import streamlit as st

from database import load_settings
from strategy import build_monthly_plan, generate_recommendations
from utils.formatting import format_currency
from utils.ui import bootstrap_page, investment_ideas_frame


bootstrap_page("Monthly Plan")

settings = load_settings()
monthly_amount = st.number_input(
    "Amount to invest this month",
    min_value=0.0,
    value=float(settings.get("monthly_investment", 1000)),
    step=50.0,
)
force = st.checkbox("Refresh market data before calculation", value=False)
persist = st.checkbox("Save this plan in SQLite", value=True)

if st.button("Generate monthly plan"):
    recommendations, summary = generate_recommendations(force_market_refresh=force)
    plan = build_monthly_plan(monthly_amount, recommendations, summary, settings, persist=persist)
    currency = settings.get("base_currency", "EUR")

    st.subheader("Suggested allocation")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Budget", format_currency(plan["monthly_amount"], currency))
    col2.metric("ETF", format_currency(plan["bucket_amounts"]["ETF"], currency))
    col3.metric("Stocks", format_currency(plan["bucket_amounts"]["ACTION"], currency))
    col4.metric("Cash / opportunities", format_currency(plan["bucket_amounts"]["CASH"], currency))

    for warning in plan["warnings"]:
        st.warning(warning)

    st.subheader("Candidates to review for monthly allocation")
    if plan["items"]:
        st.dataframe(investment_ideas_frame(plan["items"], include_plan_amount=True), use_container_width=True, hide_index=True)
    else:
        st.info("No idea passed prudence filters. Unallocated amount remains in cash.")

    st.subheader("Watch list")
    if plan["watch_items"]:
        watch_rows = [
            {
                "Ticker": item["ticker"],
                "Name": item["name"],
                "Type": item["asset_type"],
                "Score": item["score"],
                "Signal": item["prudence_level"],
                "Risk level": item.get("risk_level", "unknown"),
                "Max theoretical amount": item.get("max_theoretical_amount", 0.0),
                "Idea rationale": item.get("idea_reason", ""),
                "Risk points": " | ".join(item.get("vigilance_points", [])),
                "Validation": item.get("manual_decision", "Final decision requires manual validation by the investor."),
            }
            for item in plan["watch_items"]
        ]
        st.dataframe(pd.DataFrame(watch_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No additional line to monitor for this run.")

    st.info(plan["disclaimer"])
else:
    st.info("Click the button to generate a proposal based on current allocation.")
