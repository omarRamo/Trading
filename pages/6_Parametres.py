from __future__ import annotations

import pandas as pd
import streamlit as st

from config import RISK_PROFILES
from database import (
    get_assets,
    get_notification_preferences,
    list_notification_deliveries,
    load_settings,
    save_settings,
    seed_demo_portfolio,
    set_asset_active,
    upsert_notification_preferences,
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
    auto_sync = st.checkbox("Synchroniser automatiquement les donnees de marche", value=bool(settings.get("auto_sync_market_data", True)))
    sync_interval = st.number_input(
        "Intervalle de synchronisation marche (heures)",
        min_value=1.0,
        max_value=48.0,
        value=float(settings.get("auto_sync_interval_hours", 6)),
        step=1.0,
    )
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
                "auto_sync_market_data": auto_sync,
                "auto_sync_interval_hours": sync_interval,
            }
        )
        st.success("Parametres sauvegardes.")
        st.rerun()

st.subheader("Watchlist Revolut")
assets = get_assets(active_only=False)
st.dataframe(assets, use_container_width=True, hide_index=True)

st.subheader("Notifications email")
notification_prefs = get_notification_preferences()
with st.form("notification_settings_form"):
    notif_enabled = st.checkbox(
        "Activer les emails de recommandations",
        value=bool(notification_prefs.get("is_enabled", False)),
    )
    notif_email = st.text_input(
        "Email de destination",
        value=str(notification_prefs.get("email", "")),
        placeholder="you@example.com",
    )
    coln1, coln2, coln3 = st.columns(3)
    with coln1:
        notif_min_score = st.slider(
            "Score minimum",
            min_value=0.0,
            max_value=100.0,
            value=float(notification_prefs.get("min_score", 60.0)),
            step=1.0,
        )
    with coln2:
        notif_max_items = st.number_input(
            "Nombre max d'idees",
            min_value=1,
            max_value=30,
            value=int(notification_prefs.get("max_items", 10)),
            step=1,
        )
    with coln3:
        notif_hour = st.number_input(
            "Heure d'envoi UTC",
            min_value=0,
            max_value=23,
            value=int(notification_prefs.get("send_hour_utc", 7)),
            step=1,
        )

    notif_asset_types = st.multiselect(
        "Types d'actifs inclus",
        ["ETF", "ACTION"],
        default=list(notification_prefs.get("asset_types", ["ETF", "ACTION"])),
    )
    notif_frequency = st.selectbox(
        "Frequence",
        ["manual", "daily"],
        index=0 if str(notification_prefs.get("frequency", "manual")) != "daily" else 1,
    )
    notif_submitted = st.form_submit_button("Sauvegarder les notifications")

if notif_submitted:
    if notif_enabled and not notif_email.strip():
        st.error("Renseigne un email de destination avant d'activer l'envoi.")
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
        st.success("Parametres de notification sauvegardes.")
        st.rerun()

delivery_history = list_notification_deliveries(limit=10)
if not delivery_history.empty:
    st.caption("Historique des 10 derniers envois")
    st.dataframe(delivery_history, use_container_width=True, hide_index=True)

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
