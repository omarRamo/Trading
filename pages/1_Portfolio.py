from __future__ import annotations

from datetime import date

import streamlit as st

from charts import allocation_gap_bar, allocation_pie
from database import delete_position, get_assets, load_settings, save_settings, upsert_asset, upsert_position
from portfolio import compute_portfolio_summary, sector_exposure
from risk_management import generate_risk_alerts
from utils.formatting import format_percent
from utils.ui import bootstrap_page, metrics_row, render_alerts


bootstrap_page("Portfolio")

settings = load_settings()
summary = compute_portfolio_summary(settings)
positions = summary["positions"]

metrics_row(summary)

with st.expander("Update my personal amounts", expanded=True):
    st.caption(
        "These amounts stay local and are used for monthly planning, cash alerts, and concentration limits."
    )
    with st.form("quick_personal_amounts"):
        col1, col2, col3 = st.columns(3)
        with col1:
            cash_available = st.number_input(
                "Available amount to invest",
                min_value=0.0,
                value=float(settings.get("cash_available", 0)),
                step=50.0,
            )
        with col2:
            monthly_investment = st.number_input(
                "Monthly budget",
                min_value=0.0,
                value=float(settings.get("monthly_investment", 1000)),
                step=50.0,
            )
        with col3:
            capital_total = st.number_input(
                "Reference total capital",
                min_value=0.0,
                value=float(settings.get("capital_total", 0)),
                step=100.0,
            )
        amount_submitted = st.form_submit_button("Save these amounts")
    if amount_submitted:
        save_settings(
            {
                "cash_available": cash_available,
                "monthly_investment": monthly_investment,
                "capital_total": capital_total,
            }
        )
        st.success("Personal amounts updated.")
        st.rerun()

tab_summary, tab_edit, tab_delete = st.tabs(["Overview", "Add / Edit", "Delete"])

with tab_summary:
    left, right = st.columns(2)
    with left:
        st.plotly_chart(allocation_pie(summary["allocation_current"], "Current allocation"), use_container_width=True)
    with right:
        st.plotly_chart(allocation_gap_bar(summary["allocation_current"], summary["allocation_target"]), use_container_width=True)

    st.subheader("Alerts")
    render_alerts(generate_risk_alerts(summary, settings))

    st.subheader("Detailed positions")
    if positions.empty:
        st.info("No positions yet.")
    else:
        display = positions.copy()
        display["weight"] = display["weight"].map(format_percent)
        display["unrealized_pnl_pct"] = display["unrealized_pnl_pct"].map(format_percent)
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.subheader("Sector exposure")
    sectors = sector_exposure(summary)
    if sectors.empty:
        st.info("No sector exposure available.")
    else:
        sectors["weight"] = sectors["weight"].map(format_percent)
        st.dataframe(sectors, use_container_width=True, hide_index=True)

with tab_edit:
    assets = get_assets(active_only=True)
    existing_tickers = positions["ticker"].tolist() if not positions.empty else []
    choices = ["New position"] + existing_tickers + ["Manual watchlist entry"]
    selected_mode = st.selectbox("Mode", choices)
    asset_defaults = {}
    position_defaults = {}
    if selected_mode in existing_tickers:
        position_defaults = positions[positions["ticker"] == selected_mode].iloc[0].to_dict()
        asset_match = assets[assets["ticker"] == selected_mode]
        if not asset_match.empty:
            asset_defaults = asset_match.iloc[0].to_dict()
    elif selected_mode == "Manual watchlist entry":
        watchlist_choices = ["Select"] + assets["ticker"].tolist()
        selected_watchlist = st.selectbox("Ticker from watchlist", watchlist_choices)
        if selected_watchlist != "Select":
            asset_defaults = assets[assets["ticker"] == selected_watchlist].iloc[0].to_dict()

    ticker_default = position_defaults.get("ticker", asset_defaults.get("ticker", ""))
    name_default = position_defaults.get("name", asset_defaults.get("name", ""))
    asset_type_default = position_defaults.get("asset_type", asset_defaults.get("asset_type", "ETF"))
    currency_default = position_defaults.get("currency", asset_defaults.get("currency", settings.get("base_currency", "EUR")))
    sector_default = position_defaults.get("sector", asset_defaults.get("sector", ""))
    purchase_default = position_defaults.get("purchase_date") or date.today().isoformat()
    try:
        purchase_date_default = date.fromisoformat(str(purchase_default)[:10])
    except ValueError:
        purchase_date_default = date.today()

    with st.form("position_form"):
        ticker = st.text_input("Ticker", value=ticker_default)
        name = st.text_input("Asset name", value=name_default)
        asset_type = st.selectbox("Type", ["ETF", "ACTION"], index=0 if asset_type_default == "ETF" else 1)
        quantity = st.number_input("Held quantity", min_value=0.0, value=float(position_defaults.get("quantity", 0.0)), step=0.01)
        avg_buy_price = st.number_input("Average buy price", min_value=0.0, value=float(position_defaults.get("avg_buy_price", 0.0)), step=0.01)
        purchase_date = st.date_input("Purchase date", value=purchase_date_default)
        currency = st.text_input("Currency", value=currency_default)
        invested_amount = st.number_input(
            "Invested amount",
            min_value=0.0,
            value=float(position_defaults.get("invested_amount", 0.0)),
            step=10.0,
        )
        fees = st.number_input("Fees", min_value=0.0, value=float(position_defaults.get("fees", 0.0)), step=0.1)
        sector = st.text_input("Sector", value=sector_default)
        submitted = st.form_submit_button("Save position")

    if submitted:
        if not ticker.strip() or not name.strip():
            st.error("Ticker and name are required.")
        elif quantity <= 0 or avg_buy_price <= 0:
            st.error("Quantity and average price must be greater than zero.")
        else:
            upsert_asset(
                {
                    "ticker": ticker,
                    "name": name,
                    "asset_type": asset_type,
                    "currency": currency,
                    "sector": sector,
                    "region": asset_defaults.get("region", ""),
                    "category": asset_defaults.get("category", ""),
                    "is_active": 1,
                    "revolut_available": 1,
                    "notes": asset_defaults.get("notes", ""),
                }
            )
            upsert_position(
                {
                    "ticker": ticker,
                    "name": name,
                    "asset_type": asset_type,
                    "quantity": quantity,
                    "avg_buy_price": avg_buy_price,
                    "purchase_date": purchase_date.isoformat(),
                    "currency": currency,
                    "invested_amount": invested_amount or quantity * avg_buy_price + fees,
                    "fees": fees,
                    "sector": sector,
                }
            )
            st.success("Position saved.")
            st.rerun()

with tab_delete:
    if positions.empty:
        st.info("No position to delete.")
    else:
        ticker_to_delete = st.selectbox("Position", positions["ticker"].tolist())
        st.warning("Local deletion only: this does not change anything in Revolut.")
        if st.button("Delete this position"):
            delete_position(ticker_to_delete)
            st.success("Position deleted.")
            st.rerun()
