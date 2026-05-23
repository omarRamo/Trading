from __future__ import annotations

import pandas as pd
import streamlit as st

from strategy import generate_recommendations
from utils.formatting import format_percent
from utils.ui import bootstrap_page, investment_ideas_frame


bootstrap_page("Idées d'investissement")

st.info(
    "Ces idées sont des candidats à analyser, pas des ordres. "
    "Le signal pédagogique aide à trier: intéressant, à surveiller, attendre ou éviter."
)

col1, col2 = st.columns([1, 2])
with col1:
    force = st.checkbox("Forcer le telechargement yfinance", value=False)
with col2:
    persist = st.checkbox("Sauvegarder le classement dans SQLite", value=True)

if st.button("Calculer les idées"):
    ideas, _ = generate_recommendations(force_market_refresh=force, persist=persist)
    if not ideas:
        st.info("Aucun actif actif dans la watchlist.")
        st.stop()

    st.subheader("Candidats à analyser")
    st.dataframe(investment_ideas_frame(ideas), use_container_width=True, hide_index=True)

    st.subheader("Indicateurs utilisés")
    metric_rows = []
    for idea in ideas:
        metrics = idea.get("metrics", {})
        metric_rows.append(
            {
                "Ticker": idea["ticker"],
                "Prix": metrics.get("price"),
                "Perf 1 mois": metrics.get("perf_1m"),
                "Perf 6 mois": metrics.get("perf_6m"),
                "RSI14": metrics.get("rsi14"),
                "Volatilite": metrics.get("volatility"),
                "Statut": metrics.get("status"),
            }
        )
    metrics_df = pd.DataFrame(metric_rows)
    for col in ["Perf 1 mois", "Perf 6 mois", "Volatilite"]:
        metrics_df[col] = metrics_df[col].map(format_percent)
    st.dataframe(metrics_df, use_container_width=True, hide_index=True)

    st.info(ideas[0]["disclaimer"])
else:
    st.info("Le moteur classe les actifs de 0 a 100 selon des regles techniques, d'allocation et de risque. Il ne remplace pas ta decision finale.")
