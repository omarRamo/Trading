from __future__ import annotations

import pandas as pd
import streamlit as st

import database as db
from email_notifications import send_recommendations_digest
from strategy import generate_recommendations
from utils.formatting import format_percent
from utils.ui import bootstrap_page, investment_ideas_frame


bootstrap_page("Investment Ideas")

st.info(
    "These ideas are candidates to review, not orders. "
    "Signals help prioritize: interesting, watch, wait, avoid."
)

col1, col2 = st.columns([1, 2])
with col1:
    force = st.checkbox("Force yfinance refresh", value=False)
with col2:
    persist = st.checkbox("Save ranking in SQLite", value=True)

if st.button("Compute ideas"):
    ideas, summary = generate_recommendations(force_market_refresh=force, persist=persist)
    if not ideas:
        st.info("No active asset in watchlist.")
        st.stop()

    st.session_state["latest_ideas"] = ideas
    st.session_state["latest_summary"] = summary
else:
    st.info("The engine ranks assets from 0 to 100 using technical, allocation, and risk rules. It does not replace your final decision.")

if st.session_state.get("latest_ideas"):
    ideas = list(st.session_state.get("latest_ideas", []))
    summary = st.session_state.get("latest_summary", {})

    st.subheader("Today's prioritization")
    top_score = max((float(item.get("score", 0)) for item in ideas), default=0.0)
    actionable = [
        item
        for item in ideas
        if float(item.get("score", 0)) >= 75 and item.get("prudence_level") in {"interesting", "watch"}
    ]
    watch = [
        item
        for item in ideas
        if item.get("prudence_level") in {"watch", "wait"}
    ]
    colm1, colm2, colm3, colm4 = st.columns(4)
    colm1.metric("Total ideas", len(ideas))
    colm2.metric("Actionable", len(actionable))
    colm3.metric("Top score", f"{top_score:.1f}")
    colm4.metric("To monitor", len(watch))

    st.subheader("Filters")
    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        selected_types = st.multiselect("Asset type", ["ETF", "ACTION"], default=["ETF", "ACTION"])
    with colf2:
        min_score = st.slider("Minimum score", min_value=0.0, max_value=100.0, value=55.0, step=1.0)
    with colf3:
        selected_signals = st.multiselect(
            "Signal",
            ["interesting", "watch", "wait", "avoid"],
            default=["interesting", "watch", "wait"],
        )

    filtered = [
        item
        for item in ideas
        if item.get("asset_type") in selected_types
        and float(item.get("score", 0)) >= min_score
        and item.get("prudence_level") in selected_signals
    ]

    tab_now, tab_watch, tab_all, tab_metrics = st.tabs(
        ["Act now", "Monitor", "All ideas", "Indicators used"]
    )

    with tab_now:
        now_rows = [
            item
            for item in filtered
            if float(item.get("score", 0)) >= 75 and item.get("prudence_level") != "avoid"
        ]
        if now_rows:
            st.dataframe(investment_ideas_frame(now_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No immediate idea with current filters.")

    with tab_watch:
        watch_rows = [
            item
            for item in filtered
            if item.get("prudence_level") in {"watch", "wait"}
        ]
        if watch_rows:
            st.dataframe(investment_ideas_frame(watch_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No idea to monitor with these filters.")

    with tab_all:
        if filtered:
            st.dataframe(investment_ideas_frame(filtered), use_container_width=True, hide_index=True)
        else:
            st.warning("No result after filtering.")

    with tab_metrics:
        metric_rows = []
        for idea in filtered:
            metrics = idea.get("metrics", {})
            metric_rows.append(
                {
                    "Ticker": idea["ticker"],
                    "Price": metrics.get("price"),
                    "Perf 1 month": metrics.get("perf_1m"),
                    "Perf 6 months": metrics.get("perf_6m"),
                    "RSI14": metrics.get("rsi14"),
                    "Volatility": metrics.get("volatility"),
                    "Status": metrics.get("status"),
                }
            )
        metrics_df = pd.DataFrame(metric_rows)
        if not metrics_df.empty:
            for col in ["Perf 1 month", "Perf 6 months", "Volatility"]:
                metrics_df[col] = metrics_df[col].map(format_percent)
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)
        else:
            st.info("No indicator to display.")

    if ideas:
        st.info(ideas[0]["disclaimer"])

    st.subheader("Email delivery")
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
            "Recipient",
            value=str(prefs.get("email", "")),
            help="Address that will receive the filtered recommendation digest.",
        )
    with coln2:
        st.write("")
        send_now = st.button("Send digest")

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
