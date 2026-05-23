from __future__ import annotations

from datetime import date

import streamlit as st

from charts import allocation_gap_bar, allocation_pie
from database import delete_position, get_assets, load_settings, save_settings, upsert_asset, upsert_position
from portfolio import compute_portfolio_summary, sector_exposure
from risk_management import generate_risk_alerts
from utils.formatting import format_percent
from utils.ui import bootstrap_page, metrics_row, render_alerts


bootstrap_page("Portefeuille")

settings = load_settings()
summary = compute_portfolio_summary(settings)
positions = summary["positions"]

metrics_row(summary)

with st.expander("Mettre a jour mes montants personnels", expanded=True):
    st.caption(
        "Ces montants restent locaux et servent au plan mensuel, aux alertes de cash et aux plafonds de concentration."
    )
    with st.form("quick_personal_amounts"):
        col1, col2, col3 = st.columns(3)
        with col1:
            cash_available = st.number_input(
                "Montant disponible pour investir",
                min_value=0.0,
                value=float(settings.get("cash_available", 0)),
                step=50.0,
            )
        with col2:
            monthly_investment = st.number_input(
                "Enveloppe mensuelle",
                min_value=0.0,
                value=float(settings.get("monthly_investment", 1000)),
                step=50.0,
            )
        with col3:
            capital_total = st.number_input(
                "Capital total de reference",
                min_value=0.0,
                value=float(settings.get("capital_total", 0)),
                step=100.0,
            )
        amount_submitted = st.form_submit_button("Sauvegarder ces montants")
    if amount_submitted:
        save_settings(
            {
                "cash_available": cash_available,
                "monthly_investment": monthly_investment,
                "capital_total": capital_total,
            }
        )
        st.success("Montants personnels mis a jour.")
        st.rerun()

tab_summary, tab_edit, tab_delete = st.tabs(["Synthese", "Ajouter / modifier", "Supprimer"])

with tab_summary:
    left, right = st.columns(2)
    with left:
        st.plotly_chart(allocation_pie(summary["allocation_current"], "Allocation actuelle"), use_container_width=True)
    with right:
        st.plotly_chart(allocation_gap_bar(summary["allocation_current"], summary["allocation_target"]), use_container_width=True)

    st.subheader("Alertes")
    render_alerts(generate_risk_alerts(summary, settings))

    st.subheader("Positions detaillees")
    if positions.empty:
        st.info("Aucune position pour le moment.")
    else:
        display = positions.copy()
        display["weight"] = display["weight"].map(format_percent)
        display["unrealized_pnl_pct"] = display["unrealized_pnl_pct"].map(format_percent)
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.subheader("Exposition sectorielle")
    sectors = sector_exposure(summary)
    if sectors.empty:
        st.info("Aucune exposition sectorielle disponible.")
    else:
        sectors["weight"] = sectors["weight"].map(format_percent)
        st.dataframe(sectors, use_container_width=True, hide_index=True)

with tab_edit:
    assets = get_assets(active_only=True)
    existing_tickers = positions["ticker"].tolist() if not positions.empty else []
    choices = ["Nouvelle position"] + existing_tickers + ["Saisie manuelle watchlist"]
    selected_mode = st.selectbox("Mode", choices)
    asset_defaults = {}
    position_defaults = {}
    if selected_mode in existing_tickers:
        position_defaults = positions[positions["ticker"] == selected_mode].iloc[0].to_dict()
        asset_match = assets[assets["ticker"] == selected_mode]
        if not asset_match.empty:
            asset_defaults = asset_match.iloc[0].to_dict()
    elif selected_mode == "Saisie manuelle watchlist":
        watchlist_choices = ["Choisir"] + assets["ticker"].tolist()
        selected_watchlist = st.selectbox("Ticker depuis la watchlist", watchlist_choices)
        if selected_watchlist != "Choisir":
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
        name = st.text_input("Nom de l'actif", value=name_default)
        asset_type = st.selectbox("Type", ["ETF", "ACTION"], index=0 if asset_type_default == "ETF" else 1)
        quantity = st.number_input("Quantite detenue", min_value=0.0, value=float(position_defaults.get("quantity", 0.0)), step=0.01)
        avg_buy_price = st.number_input("Prix moyen d'achat", min_value=0.0, value=float(position_defaults.get("avg_buy_price", 0.0)), step=0.01)
        purchase_date = st.date_input("Date d'achat", value=purchase_date_default)
        currency = st.text_input("Devise", value=currency_default)
        invested_amount = st.number_input(
            "Montant investi",
            min_value=0.0,
            value=float(position_defaults.get("invested_amount", 0.0)),
            step=10.0,
        )
        fees = st.number_input("Frais eventuels", min_value=0.0, value=float(position_defaults.get("fees", 0.0)), step=0.1)
        sector = st.text_input("Secteur", value=sector_default)
        submitted = st.form_submit_button("Enregistrer la position")

    if submitted:
        if not ticker.strip() or not name.strip():
            st.error("Ticker et nom sont obligatoires.")
        elif quantity <= 0 or avg_buy_price <= 0:
            st.error("Quantite et prix moyen doivent etre superieurs a zero.")
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
            st.success("Position enregistree.")
            st.rerun()

with tab_delete:
    if positions.empty:
        st.info("Aucune position a supprimer.")
    else:
        ticker_to_delete = st.selectbox("Position", positions["ticker"].tolist())
        st.warning("Suppression locale uniquement: cela ne modifie rien sur Revolut.")
        if st.button("Supprimer cette position"):
            delete_position(ticker_to_delete)
            st.success("Position supprimee.")
            st.rerun()
