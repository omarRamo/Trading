from __future__ import annotations

import pandas as pd
import streamlit as st

from config import RISK_PROFILES
import database as db
from database import (
    get_assets,
    load_settings,
    save_settings,
    seed_demo_portfolio,
    set_asset_active,
    upsert_asset,
)
from utils.i18n import SUPPORTED_LANGUAGES, current_language, set_language
from utils.ui import bootstrap_page


bootstrap_page("Settings")

settings = load_settings()

st.subheader("Investor configuration")
with st.form("settings_form"):
    language = current_language(settings)
    language_options = list(SUPPORTED_LANGUAGES.keys())
    app_language = st.selectbox(
        "App language",
        language_options,
        index=language_options.index(language) if language in language_options else 0,
        format_func=lambda code: SUPPORTED_LANGUAGES.get(code, code),
    )

    capital_total = st.number_input("Current total capital", min_value=0.0, value=float(settings.get("capital_total", 0)), step=100.0)
    cash_available = st.number_input("Available cash", min_value=0.0, value=float(settings.get("cash_available", 0)), step=50.0)
    monthly_investment = st.number_input("Monthly amount to invest", min_value=0.0, value=float(settings.get("monthly_investment", 1000)), step=50.0)

    col1, col2, col3 = st.columns(3)
    with col1:
        etf_pct = st.number_input("ETF allocation (%)", min_value=0.0, max_value=100.0, value=float(settings.get("target_allocation_etf", 0.7)) * 100, step=1.0)
    with col2:
        stock_pct = st.number_input("Stock allocation (%)", min_value=0.0, max_value=100.0, value=float(settings.get("target_allocation_stocks", 0.2)) * 100, step=1.0)
    with col3:
        cash_pct = st.number_input("Cash allocation (%)", min_value=0.0, max_value=100.0, value=float(settings.get("target_allocation_cash", 0.1)) * 100, step=1.0)

    base_currency = st.text_input("Base currency", value=settings.get("base_currency", "EUR"))
    max_position = st.slider(
        "Max risk per individual stock",
        min_value=0.05,
        max_value=0.10,
        value=float(settings.get("max_individual_position", 0.08)),
        step=0.005,
        format="%.3f",
    )
    risk_per_trade_pct = st.number_input(
        "Risk per trade (%)",
        min_value=0.1,
        max_value=5.0,
        value=float(settings.get("risk_per_trade_pct", 0.01)) * 100,
        step=0.1,
    )
    default_rr_target = st.number_input(
        "Default target R/R",
        min_value=0.5,
        max_value=10.0,
        value=float(settings.get("default_rr_target", 2.0)),
        step=0.1,
    )
    risk_profile = st.selectbox(
        "Risk profile",
        RISK_PROFILES,
        index=RISK_PROFILES.index(settings.get("risk_profile", "equilibre")) if settings.get("risk_profile", "equilibre") in RISK_PROFILES else 1,
    )
    investment_horizon = st.text_input("Investment horizon", value=settings.get("investment_horizon", "long term"))
    tech_limit = st.slider("Technology exposure alert", min_value=0.20, max_value=0.80, value=float(settings.get("tech_exposure_limit", 0.45)), step=0.05)
    auto_sync = st.checkbox("Automatically sync market data", value=bool(settings.get("auto_sync_market_data", True)))
    sync_interval = st.number_input(
        "Market sync interval (hours)",
        min_value=1.0,
        max_value=48.0,
        value=float(settings.get("auto_sync_interval_hours", 6)),
        step=1.0,
    )

    submitted = st.form_submit_button("Save settings")

if submitted:
    total_pct = etf_pct + stock_pct + cash_pct
    if abs(total_pct - 100.0) > 0.01:
        st.error(f"Allocations must total 100%, current total: {total_pct:.1f}%.")
    else:
        save_settings(
            {
                "app_language": app_language,
                "capital_total": capital_total,
                "cash_available": cash_available,
                "monthly_investment": monthly_investment,
                "target_allocation_etf": etf_pct / 100,
                "target_allocation_stocks": stock_pct / 100,
                "target_allocation_cash": cash_pct / 100,
                "base_currency": base_currency.upper().strip() or "EUR",
                "max_individual_position": max_position,
                "hard_max_individual_position": 0.10,
                "risk_per_trade_pct": risk_per_trade_pct / 100,
                "default_rr_target": default_rr_target,
                "risk_profile": risk_profile,
                "investment_horizon": investment_horizon,
                "tech_exposure_limit": tech_limit,
                "auto_sync_market_data": auto_sync,
                "auto_sync_interval_hours": sync_interval,
            }
        )
        set_language(app_language)
        st.success("Settings saved.")
        st.rerun()

st.subheader("Revolut watchlist")
assets = get_assets(active_only=False)
st.dataframe(assets, use_container_width=True, hide_index=True)

st.subheader("Email notifications")
get_notification_preferences = getattr(db, "get_notification_preferences", None)
upsert_notification_preferences = getattr(db, "upsert_notification_preferences", None)
list_notification_deliveries = getattr(db, "list_notification_deliveries", None)

notification_prefs = (
    get_notification_preferences()
    if callable(get_notification_preferences)
    else {
        "is_enabled": False,
        "email": "",
        "min_score": 60.0,
        "asset_types": ["ETF", "ACTION"],
        "max_items": 10,
        "frequency": "manual",
        "send_hour_utc": 7,
    }
)

with st.form("notification_settings_form"):
    notif_enabled = st.checkbox("Enable recommendation emails", value=bool(notification_prefs.get("is_enabled", False)))
    notif_email = st.text_input("Destination email", value=str(notification_prefs.get("email", "")), placeholder="you@example.com")

    coln1, coln2, coln3 = st.columns(3)
    with coln1:
        notif_min_score = st.slider("Minimum score", min_value=0.0, max_value=100.0, value=float(notification_prefs.get("min_score", 60.0)), step=1.0)
    with coln2:
        notif_max_items = st.number_input("Max number of ideas", min_value=1, max_value=30, value=int(notification_prefs.get("max_items", 10)), step=1)
    with coln3:
        notif_hour = st.number_input("UTC send hour", min_value=0, max_value=23, value=int(notification_prefs.get("send_hour_utc", 7)), step=1)

    notif_asset_types = st.multiselect("Included asset types", ["ETF", "ACTION"], default=list(notification_prefs.get("asset_types", ["ETF", "ACTION"])))
    notif_frequency = st.selectbox("Frequency", ["manual", "daily"], index=0 if str(notification_prefs.get("frequency", "manual")) != "daily" else 1)
    notif_submitted = st.form_submit_button("Save notifications")

if notif_submitted:
    if notif_enabled and not notif_email.strip():
        st.error("Provide a destination email before enabling notifications.")
    elif not callable(upsert_notification_preferences):
        st.warning("Notification module is unavailable in this version. Update required.")
    else:
        upsert_notification_preferences(
            {
                "is_enabled": notif_enabled,
                "email": notif_email.strip(),
                "min_score": notif_min_score,
                "asset_types": notif_asset_types or ["ETF", "ACTION"],
                "max_items": int(notif_max_items),
                "frequency": notif_frequency,
                "send_hour_utc": int(notif_hour),
            }
        )
        st.success("Notification settings saved.")
        st.rerun()

delivery_history = list_notification_deliveries(limit=10) if callable(list_notification_deliveries) else pd.DataFrame()
if not delivery_history.empty:
    st.caption("Last 10 deliveries")
    st.dataframe(delivery_history, use_container_width=True, hide_index=True)

with st.form("asset_form"):
    ticker = st.text_input("Ticker")
    name = st.text_input("Name")
    asset_type = st.selectbox("Type", ["ETF", "ACTION"])
    currency = st.text_input("Currency", value=settings.get("base_currency", "EUR"))
    sector = st.text_input("Sector")
    region = st.text_input("Region")
    category = st.text_input("Category")
    revolut_available = st.checkbox("Available in my Revolut watchlist", value=True)
    notes = st.text_area("Notes")
    asset_submitted = st.form_submit_button("Add / update asset")

if asset_submitted:
    if not ticker.strip() or not name.strip():
        st.error("Ticker and name are required.")
    else:
        upsert_asset(
            {
                "ticker": ticker,
                "name": name,
                "asset_type": asset_type,
                "currency": currency.upper().strip() or "EUR",
                "sector": sector,
                "region": region,
                "category": category,
                "is_active": 1,
                "revolut_available": int(revolut_available),
                "notes": notes,
            }
        )
        st.success("Asset saved.")
        st.rerun()

if not assets.empty:
    st.subheader("Enable / disable ticker")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        ticker_toggle = st.selectbox("Ticker", assets["ticker"].tolist())
    with col2:
        if st.button("Enable"):
            set_asset_active(ticker_toggle, True)
            st.rerun()
    with col3:
        if st.button("Disable"):
            set_asset_active(ticker_toggle, False)
            st.rerun()

st.subheader("Sample data")
overwrite = st.checkbox("Replace existing sample portfolio")
if st.button("Load sample portfolio"):
    seed_demo_portfolio(overwrite=overwrite)
    st.success("Sample portfolio loaded.")
    st.rerun()

st.subheader("Built-in strict rules")
st.markdown(
    """
- No leverage, margin trading, short selling, or automatic execution.
- No buy suggestion for a stock already above the configured limit.
- Penalties when RSI > 70, volatility is high, or trend is fragile.
- ETFs may have larger weights than individual stocks.
- Alerts when cash is too low, concentration is excessive, tech exposure is high, or correlations are strong.
"""
)
