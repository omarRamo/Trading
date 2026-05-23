from __future__ import annotations

from datetime import date

import streamlit as st

from database import add_transaction, get_assets, get_transactions, load_settings
from utils.ui import bootstrap_page


bootstrap_page("Transactions")

settings = load_settings()
assets = get_assets(active_only=True)
choices = ["Saisie manuelle"] + assets["ticker"].tolist()
selected = st.selectbox("Actif", choices)
defaults = {}
if selected != "Saisie manuelle":
    defaults = assets[assets["ticker"] == selected].iloc[0].to_dict()

with st.form("transaction_form"):
    ticker = st.text_input("Ticker", value=defaults.get("ticker", ""))
    asset_name = st.text_input("Nom", value=defaults.get("name", ""))
    asset_type = st.selectbox("Type", ["ETF", "ACTION"], index=0 if defaults.get("asset_type", "ETF") == "ETF" else 1)
    transaction_type = st.selectbox("Operation", ["BUY", "SELL"])
    quantity = st.number_input("Quantite", min_value=0.0, value=0.0, step=0.01)
    price = st.number_input("Prix", min_value=0.0, value=0.0, step=0.01)
    transaction_date = st.date_input("Date", value=date.today())
    currency = st.text_input("Devise", value=defaults.get("currency", settings.get("base_currency", "EUR")))
    fees = st.number_input("Frais", min_value=0.0, value=0.0, step=0.1)
    notes = st.text_area("Notes")
    update_position = st.checkbox("Mettre a jour la position si achat", value=True)
    submitted = st.form_submit_button("Enregistrer la transaction")

if submitted:
    if not ticker.strip() or quantity <= 0 or price <= 0:
        st.error("Ticker, quantite et prix sont obligatoires.")
    else:
        add_transaction(
            {
                "ticker": ticker,
                "asset_name": asset_name or ticker,
                "asset_type": asset_type,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "price": price,
                "transaction_date": transaction_date.isoformat(),
                "currency": currency.upper().strip() or settings.get("base_currency", "EUR"),
                "fees": fees,
                "amount": quantity * price + fees,
                "notes": notes,
            },
            update_position=update_position,
        )
        st.success("Transaction enregistree localement.")
        st.rerun()

st.subheader("Historique local")
transactions = get_transactions()
if transactions.empty:
    st.info("Aucune transaction enregistree.")
else:
    st.dataframe(transactions, use_container_width=True, hide_index=True)
