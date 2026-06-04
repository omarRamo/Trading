from __future__ import annotations

import pandas as pd
import streamlit as st

import database as db
from email_notifications import send_recommendations_digest
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
    ideas, summary = generate_recommendations(force_market_refresh=force, persist=persist)
    if not ideas:
        st.info("Aucun actif actif dans la watchlist.")
        st.stop()

    st.session_state["latest_ideas"] = ideas
    st.session_state["latest_summary"] = summary
else:
    st.info("Le moteur classe les actifs de 0 a 100 selon des regles techniques, d'allocation et de risque. Il ne remplace pas ta decision finale.")

if st.session_state.get("latest_ideas"):
    ideas = list(st.session_state.get("latest_ideas", []))
    summary = st.session_state.get("latest_summary", {})

    st.subheader("Priorisation du jour")
    top_score = max((float(item.get("score", 0)) for item in ideas), default=0.0)
    actionable = [
        item
        for item in ideas
        if float(item.get("score", 0)) >= 75 and item.get("prudence_level") in {"intéressant", "à surveiller"}
    ]
    watch = [
        item
        for item in ideas
        if item.get("prudence_level") in {"à surveiller", "attendre"}
    ]
    colm1, colm2, colm3, colm4 = st.columns(4)
    colm1.metric("Idees totales", len(ideas))
    colm2.metric("Actionnables", len(actionable))
    colm3.metric("Top score", f"{top_score:.1f}")
    colm4.metric("A surveiller", len(watch))

    st.subheader("Filtres")
    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        selected_types = st.multiselect("Type d'actif", ["ETF", "ACTION"], default=["ETF", "ACTION"])
    with colf2:
        min_score = st.slider("Score minimum", min_value=0.0, max_value=100.0, value=55.0, step=1.0)
    with colf3:
        selected_signals = st.multiselect(
            "Signal",
            ["intéressant", "à surveiller", "attendre", "éviter"],
            default=["intéressant", "à surveiller", "attendre"],
        )

    filtered = [
        item
        for item in ideas
        if item.get("asset_type") in selected_types
        and float(item.get("score", 0)) >= min_score
        and item.get("prudence_level") in selected_signals
    ]

    tab_now, tab_watch, tab_all, tab_metrics = st.tabs(
        ["Agir maintenant", "A surveiller", "Toutes les idees", "Indicateurs utilises"]
    )

    with tab_now:
        now_rows = [
            item
            for item in filtered
            if float(item.get("score", 0)) >= 75 and item.get("prudence_level") != "éviter"
        ]
        if now_rows:
            st.dataframe(investment_ideas_frame(now_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune idee immediate selon les filtres actuels.")

    with tab_watch:
        watch_rows = [
            item
            for item in filtered
            if item.get("prudence_level") in {"à surveiller", "attendre"}
        ]
        if watch_rows:
            st.dataframe(investment_ideas_frame(watch_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune idee a surveiller avec ces filtres.")

    with tab_all:
        if filtered:
            st.dataframe(investment_ideas_frame(filtered), use_container_width=True, hide_index=True)
        else:
            st.warning("Aucun resultat apres filtrage.")

    with tab_metrics:
        metric_rows = []
        for idea in filtered:
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
        if not metrics_df.empty:
            for col in ["Perf 1 mois", "Perf 6 mois", "Volatilite"]:
                metrics_df[col] = metrics_df[col].map(format_percent)
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun indicateur a afficher.")

    if ideas:
        st.info(ideas[0]["disclaimer"])

    st.subheader("Envoi email")
    get_notification_preferences = getattr(db, "get_notification_preferences", None)
    log_notification_delivery = getattr(db, "log_notification_delivery", None)
    set_notification_last_sent = getattr(db, "set_notification_last_sent", None)
    prefs = (
        get_notification_preferences()
        if callable(get_notification_preferences)
        else {
            "email": "",
            "min_score": 60.0,
            "asset_types": ["ETF", "ACTION"],
            "max_items": 10,
            "frequency": "manual",
            "is_enabled": False,
        }
    )
    coln1, coln2 = st.columns([2, 1])
    with coln1:
        target_email = st.text_input(
            "Destinataire",
            value=str(prefs.get("email", "")),
            help="Adresse qui recevra le digest des recommandations filtrées.",
        )
    with coln2:
        st.write("")
        send_now = st.button("Envoyer le digest")

    if send_now:
        ideas = st.session_state.get("latest_ideas", [])
        summary = st.session_state.get("latest_summary")
        if summary is None:
            _, summary = generate_recommendations(force_market_refresh=False, persist=False)
        result = send_recommendations_digest(
            recommendations=ideas,
            summary=summary,
            preferences=prefs,
            target_email=target_email,
        )
        if result.ok:
            if callable(log_notification_delivery):
                log_notification_delivery(
                    email=target_email.strip(),
                    subject=result.subject,
                    status="sent",
                    item_count=result.item_count,
                )
            if callable(set_notification_last_sent):
                set_notification_last_sent()
            st.success(result.message)
        else:
            if callable(log_notification_delivery):
                log_notification_delivery(
                    email=target_email.strip(),
                    subject=result.subject or "Trading Digest",
                    status="error",
                    item_count=result.item_count,
                    error_message=result.message,
                )
            st.error(result.message)
