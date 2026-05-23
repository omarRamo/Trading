from __future__ import annotations

from datetime import date

import streamlit as st

from charts import allocation_gap_bar, allocation_pie
from database import delete_position, get_assets, load_settings, upsert_asset, upsert_position
from portfolio import compute_portfolio_summary, sector_exposure
from risk_management import generate_risk_alerts
from utils.formatting import format_percent
from utils.ui import bootstrap_page, metrics_row, render_alerts


bootstrap_page("Portefeuille")

settings = load_settings()
summary = compute_portfolio_summary(settings)
positions = summary["positions"]

metrics_row(summary)

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
    choices = ["Saisie manuelle"] + assets["ticker"].tolist()
    selected = st.selectbox("Ticker depuis la watchlist", choices)
    asset_defaults = {}
    if selected != "Saisie manuelle":
        asset_defaults = assets[assets["ticker"] == selected].iloc[0].to_dict()

    with st.form("position_form"):
        ticker = st.text_input("Ticker", value=asset_defaults.get("ticker", ""))
        name = st.text_input("Nom de l'actif", value=asset_defaults.get("name", ""))
        asset_type = st.selectbox("Type", ["ETF", "ACTION"], index=0 if asset_defaults.get("asset_type", "ETF") == "ETF" else 1)
        quantity = st.number_input("Quantite detenue", min_value=0.0, value=0.0, step=0.01)
        avg_buy_price = st.number_input("Prix moyen d'achat", min_value=0.0, value=0.0, step=0.01)
        purchase_date = st.date_input("Date d'achat", value=date.today())
        currency = st.text_input("Devise", value=asset_defaults.get("currency", settings.get("base_currency", "EUR")))
        invested_amount = st.number_input("Montant investi", min_value=0.0, value=0.0, step=10.0)
        fees = st.number_input("Frais eventuels", min_value=0.0, value=0.0, step=0.1)
        sector = st.text_input("Secteur", value=asset_defaults.get("sector", ""))
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
