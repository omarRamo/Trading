from __future__ import annotations

import streamlit as st

from database import get_assets, get_positions, get_transactions, get_user, list_users, load_settings, save_settings
from utils.ui import bootstrap_page


bootstrap_page("Profile")

user = get_user()
settings = load_settings()

st.info(
    "This profile is tied to the signed-in account. Settings, watchlist, portfolio, "
    "transactions, and monthly plans are isolated from other accounts."
)

if user:
    col1, col2 = st.columns([1, 4])
    with col1:
        if user.get("picture_url"):
            st.image(user["picture_url"], width=96)
    with col2:
        st.subheader(user.get("name") or "Google account")
        st.write(user.get("email"))
        st.caption(f"Technical profile ID: {user.get('id')}")

st.subheader("Profile data")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tracked tickers", len(get_assets(active_only=False)))
col2.metric("Positions", len(get_positions()))
col3.metric("Transactions", len(get_transactions()))
col4.metric("Currency", settings.get("base_currency", "EUR"))

st.subheader("Personal amounts")
with st.form("profile_amounts"):
    cash_available = st.number_input(
        "Available amount to invest",
        min_value=0.0,
        value=float(settings.get("cash_available", 0)),
        step=50.0,
    )
    monthly_investment = st.number_input(
        "Usual monthly budget",
        min_value=0.0,
        value=float(settings.get("monthly_investment", 1000)),
        step=50.0,
    )
    capital_total = st.number_input(
        "Reference total capital",
        min_value=0.0,
        value=float(settings.get("capital_total", 0)),
        step=100.0,
    )
    submitted = st.form_submit_button("Update my profile")

if submitted:
    save_settings(
        {
            "cash_available": cash_available,
            "monthly_investment": monthly_investment,
            "capital_total": capital_total,
        }
    )
    st.success("Profile updated.")
    st.rerun()

with st.expander("Profiles created on this local installation"):
    st.caption("Useful local list when multiple accounts use the same app.")
    st.dataframe(list_users(), use_container_width=True, hide_index=True)
