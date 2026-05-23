from __future__ import annotations

import pandas as pd
import streamlit as st

from database import load_settings
from strategy import build_monthly_plan, generate_recommendations
from utils.formatting import format_currency
from utils.ui import bootstrap_page, investment_ideas_frame


bootstrap_page("Plan mensuel")

settings = load_settings()
monthly_amount = st.number_input(
    "Montant a investir ce mois-ci",
    min_value=0.0,
    value=float(settings.get("monthly_investment", 1000)),
    step=50.0,
)
force = st.checkbox("Actualiser les donnees de marche avant de calculer", value=False)
persist = st.checkbox("Sauvegarder ce plan dans SQLite", value=True)

if st.button("Generer le plan mensuel"):
    recommendations, summary = generate_recommendations(force_market_refresh=force)
    plan = build_monthly_plan(monthly_amount, recommendations, summary, settings, persist=persist)
    currency = settings.get("base_currency", "EUR")

    st.subheader("Repartition proposee")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Enveloppe", format_currency(plan["monthly_amount"], currency))
    col2.metric("ETF", format_currency(plan["bucket_amounts"]["ETF"], currency))
    col3.metric("Actions", format_currency(plan["bucket_amounts"]["ACTION"], currency))
    col4.metric("Cash / opportunites", format_currency(plan["bucket_amounts"]["CASH"], currency))

    for warning in plan["warnings"]:
        st.warning(warning)

    st.subheader("Candidats à analyser pour la répartition mensuelle")
    if plan["items"]:
        st.dataframe(investment_ideas_frame(plan["items"], include_plan_amount=True), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune idee n'a passe les filtres de prudence. Le montant non alloue reste en cash.")

    st.subheader("Liste de surveillance")
    if plan["watch_items"]:
        watch_rows = [
            {
                "Ticker": item["ticker"],
                "Nom": item["name"],
                "Type": item["asset_type"],
                "Score": item["score"],
                "Signal pédagogique": item["prudence_level"],
                "Niveau de risque": item.get("risk_level", "inconnu"),
                "Montant maximum théorique": item.get("max_theoretical_amount", 0.0),
                "Raison de l'idée": item.get("idea_reason", ""),
                "Points de vigilance": " | ".join(item.get("vigilance_points", [])),
                "Validation": item.get("manual_decision", "Décision finale à valider manuellement par l’investisseur."),
            }
            for item in plan["watch_items"]
        ]
        st.dataframe(pd.DataFrame(watch_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Pas de ligne supplementaire a surveiller dans ce calcul.")

    st.info(plan["disclaimer"])
else:
    st.info("Clique sur le bouton pour generer une proposition a partir de l'allocation actuelle.")
