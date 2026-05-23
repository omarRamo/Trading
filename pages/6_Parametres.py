from __future__ import annotations

import pandas as pd
import streamlit as st

from config import RISK_PROFILES
from database import (
    get_assets,
    load_settings,
    save_settings,
    seed_demo_portfolio,
    set_asset_active,
    upsert_asset,
)
from utils.ui import bootstrap_page


bootstrap_page("Parametres")

settings = load_settings()

st.subheader("Configuration investisseur")
with st.form("settings_form"):
    capital_total = st.number_input("Capital total actuel", min_value=0.0, value=float(settings.get("capital_total", 0)), step=100.0)
    cash_available = st.number_input("Cash disponible", min_value=0.0, value=float(settings.get("cash_available", 0)), step=50.0)
    monthly_investment = st.number_input("Montant mensuel a investir", min_value=0.0, value=float(settings.get("monthly_investment", 1000)), step=50.0)
    col1, col2, col3 = st.columns(3)
    with col1:
        etf_pct = st.number_input("Allocation ETF (%)", min_value=0.0, max_value=100.0, value=float(settings.get("target_allocation_etf", 0.7)) * 100, step=1.0)
    with col2:
        stock_pct = st.number_input("Allocation actions (%)", min_value=0.0, max_value=100.0, value=float(settings.get("target_allocation_stocks", 0.2)) * 100, step=1.0)
    with col3:
        cash_pct = st.number_input("Allocation cash (%)", min_value=0.0, max_value=100.0, value=float(settings.get("target_allocation_cash", 0.1)) * 100, step=1.0)
    base_currency = st.text_input("Devise principale", value=settings.get("base_currency", "EUR"))
    max_position = st.slider("Risque maximum par action individuelle", min_value=0.05, max_value=0.10, value=float(settings.get("max_individual_position", 0.08)), step=0.005, format="%.3f")
    risk_profile = st.selectbox(
        "Profil de risque",
        RISK_PROFILES,
        index=RISK_PROFILES.index(settings.get("risk_profile", "equilibre")) if settings.get("risk_profile", "equilibre") in RISK_PROFILES else 1,
    )
    investment_horizon = st.text_input("Horizon d'investissement", value=settings.get("investment_horizon", "long terme"))
    tech_limit = st.slider("Alerte exposition technologie", min_value=0.20, max_value=0.80, value=float(settings.get("tech_exposure_limit", 0.45)), step=0.05)
    submitted = st.form_submit_button("Sauvegarder les parametres")

if submitted:
    total_pct = etf_pct + stock_pct + cash_pct
    if abs(total_pct - 100.0) > 0.01:
        st.error(f"Les allocations doivent totaliser 100 %, total actuel: {total_pct:.1f} %.")
    else:
        save_settings(
            {
                "capital_total": capital_total,
                "cash_available": cash_available,
                "monthly_investment": monthly_investment,
                "target_allocation_etf": etf_pct / 100,
                "target_allocation_stocks": stock_pct / 100,
                "target_allocation_cash": cash_pct / 100,
                "base_currency": base_currency.upper().strip() or "EUR",
                "max_individual_position": max_position,
                "hard_max_individual_position": 0.10,
                "risk_profile": risk_profile,
                "investment_horizon": investment_horizon,
                "tech_exposure_limit": tech_limit,
            }
        )
        st.success("Parametres sauvegardes.")
        st.rerun()

st.subheader("Watchlist Revolut")
assets = get_assets(active_only=False)
st.dataframe(assets, use_container_width=True, hide_index=True)

with st.form("asset_form"):
    ticker = st.text_input("Ticker")
    name = st.text_input("Nom")
    asset_type = st.selectbox("Type", ["ETF", "ACTION"])
    currency = st.text_input("Devise", value=settings.get("base_currency", "EUR"))
    sector = st.text_input("Secteur")
    region = st.text_input("Region")
    category = st.text_input("Categorie")
    revolut_available = st.checkbox("Disponible dans ma watchlist Revolut", value=True)
    notes = st.text_area("Notes")
    asset_submitted = st.form_submit_button("Ajouter / mettre a jour l'actif")

if asset_submitted:
    if not ticker.strip() or not name.strip():
        st.error("Ticker et nom sont obligatoires.")
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
        st.success("Actif enregistre.")
        st.rerun()

if not assets.empty:
    st.subheader("Activer / desactiver un ticker")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        ticker_toggle = st.selectbox("Ticker", assets["ticker"].tolist())
    with col2:
        if st.button("Activer"):
            set_asset_active(ticker_toggle, True)
            st.rerun()
    with col3:
        if st.button("Desactiver"):
            set_asset_active(ticker_toggle, False)
            st.rerun()

st.subheader("Donnees d'exemple")
overwrite = st.checkbox("Remplacer le portefeuille fictif existant")
if st.button("Charger l'exemple de portefeuille"):
    seed_demo_portfolio(overwrite=overwrite)
    st.success("Exemple fictif charge.")
    st.rerun()

st.subheader("Regles strictes integrees")
st.markdown(
    """
- Aucun levier, margin trading, vente a decouvert ou execution automatique.
- Aucun achat propose sur une action deja au-dessus de la limite configuree.
- Malus si RSI > 70, volatilite elevee ou tendance technique fragile.
- Les ETF peuvent peser davantage que les actions individuelles.
- Alertes si cash trop bas, concentration excessive, exposition tech elevee ou correlations fortes.
"""
)
