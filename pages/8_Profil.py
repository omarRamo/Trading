from __future__ import annotations

import streamlit as st

from database import get_assets, get_positions, get_transactions, get_user, list_users, load_settings, save_settings
from utils.ui import bootstrap_page


bootstrap_page("Profil")

user = get_user()
settings = load_settings()

st.info(
    "Ce profil est lie au compte Google connecte. Les parametres, la watchlist, le portefeuille, "
    "les transactions et les plans mensuels sont separes des autres comptes Google."
)

if user:
    col1, col2 = st.columns([1, 4])
    with col1:
        if user.get("picture_url"):
            st.image(user["picture_url"], width=96)
    with col2:
        st.subheader(user.get("name") or "Compte Google")
        st.write(user.get("email"))
        st.caption(f"Profil technique: {user.get('id')}")

st.subheader("Donnees de ce profil")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Tickers suivis", len(get_assets(active_only=False)))
col2.metric("Positions", len(get_positions()))
col3.metric("Transactions", len(get_transactions()))
col4.metric("Devise", settings.get("base_currency", "EUR"))

st.subheader("Montants personnels")
with st.form("profile_amounts"):
    cash_available = st.number_input(
        "Montant disponible pour investir",
        min_value=0.0,
        value=float(settings.get("cash_available", 0)),
        step=50.0,
    )
    monthly_investment = st.number_input(
        "Enveloppe mensuelle habituelle",
        min_value=0.0,
        value=float(settings.get("monthly_investment", 1000)),
        step=50.0,
    )
    capital_total = st.number_input(
        "Capital total de reference",
        min_value=0.0,
        value=float(settings.get("capital_total", 0)),
        step=100.0,
    )
    submitted = st.form_submit_button("Mettre a jour mon profil")

if submitted:
    save_settings(
        {
            "cash_available": cash_available,
            "monthly_investment": monthly_investment,
            "capital_total": capital_total,
        }
    )
    st.success("Profil mis a jour.")
    st.rerun()

with st.expander("Profils deja crees sur cette installation locale"):
    st.caption("Liste locale utile si plusieurs comptes Google utilisent la meme application.")
    st.dataframe(list_users(), use_container_width=True, hide_index=True)

