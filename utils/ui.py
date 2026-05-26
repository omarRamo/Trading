from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from config import DISCLAIMER
from database import initialize_database, load_settings
from market_sync import maybe_auto_sync_market_data, sync_market_data
from utils.auth import render_logout_control, require_login
from utils.formatting import format_currency, format_percent
from utils.badges import signal_badge


def bootstrap_page(title: str) -> None:
    sidebar_state = "expanded" if st.session_state.get("authenticated") else "collapsed"
    st.set_page_config(page_title=title, layout="wide", initial_sidebar_state=sidebar_state)
    initialize_database()
    require_login()
    render_logout_control()
    _render_market_sync_sidebar(title)
    st.title(title)
    st.caption(DISCLAIMER)


def _render_market_sync_sidebar(title: str) -> None:
    settings = load_settings()
    st.sidebar.divider()
    st.sidebar.subheader("Synchro marche")
    if st.sidebar.button("Synchroniser maintenant", key=f"sync_{title}"):
        with st.spinner("Synchronisation des donnees de marche..."):
            result = sync_market_data(force_refresh=True)
        st.sidebar.success(f"{result['synced']} tickers synchronises.")
        if result["errors"]:
            st.sidebar.warning(f"{len(result['errors'])} ticker(s) sans donnees.")
    else:
        with st.spinner("Verification de la synchro marche..."):
            result = maybe_auto_sync_market_data()
        if result:
            st.sidebar.success(f"Synchro auto: {result['synced']} tickers.")
            if result["errors"]:
                st.sidebar.warning(f"{len(result['errors'])} ticker(s) sans donnees.")

    refreshed_settings = load_settings()
    last_sync = refreshed_settings.get("last_market_sync_at") or "Jamais"
    auto_status = "active" if refreshed_settings.get("auto_sync_market_data", True) else "desactivee"
    st.sidebar.caption(f"Auto-sync {auto_status}. Derniere synchro: {last_sync}")


def render_alerts(alerts: list[dict[str, str]]) -> None:
    priority = {"danger": 3, "warning": 2, "info": 1, "success": 1}
    critical_keys = ("concentration", "cash")
    important_keys = ("rsi", "volatil")
    ranked = sorted(alerts, key=lambda a: priority.get(a.get("severity", "info"), 0), reverse=True)
    for alert in ranked:
        text = f"**{alert.get('title', 'Alerte')}**  \n{alert.get('message', '')}"
        content = f"{text}"
        title = (alert.get("title", "") + " " + alert.get("message", "")).lower()
        if any(k in title for k in critical_keys):
            st.error(content, icon="🚨")
        elif any(k in title for k in important_keys) or alert.get("severity") == "warning":
            st.warning(content, icon="⚠️")
        else:
            st.info(content, icon="ℹ️")


def metrics_row(summary: dict[str, Any], monthly_available: float | None = None) -> None:
    currency = summary.get("currency", "EUR")
    pnl = summary.get("unrealized_pnl", 0.0)
    worst_gap = max((abs(v) for v in summary.get("allocation_gaps", {}).values()), default=0.0)
    worst_bucket = max(summary.get("allocation_gaps", {}).items(), key=lambda x: abs(x[1]), default=("N/A", 0.0))
    badge = "🔴" if worst_gap > 0.10 else "🟢"
    cards = st.columns(4)
    cards[0].metric("Valeur totale", format_currency(summary["total_value"], currency), delta=("📈" if pnl > 0 else "📉"))
    cards[1].metric("P/L latent total", format_currency(pnl, currency), format_percent(summary.get("unrealized_pnl_pct", 0.0)))
    cards[2].metric("Allocation la + déséquilibrée", f"{badge} {worst_bucket[0]}", format_percent(worst_bucket[1]))
    cards[3].metric("Enveloppe mensuelle dispo", format_currency(monthly_available if monthly_available is not None else summary.get("cash", 0.0), currency))


def investment_ideas_frame(ideas: list[dict[str, Any]], include_plan_amount: bool = False) -> pd.DataFrame:
    rows = []
    for idea in ideas:
        row = {
            "Ticker": idea["ticker"],
            "Nom": idea.get("name", ""),
            "Type d'actif": idea["asset_type"],
            "Score de qualité": idea["score"],
            "Signal pédagogique": signal_badge(idea.get("prudence_level", "")),
            "Niveau de risque": idea.get("risk_level", "inconnu"),
            "Montant maximum théorique": idea.get("max_theoretical_amount", 0.0),
            "Raison de l'idée": idea.get("idea_reason") or " | ".join(idea.get("reasons", [])),
            "Points de vigilance": " | ".join(idea.get("vigilance_points", [])),
            "Validation": idea.get("manual_decision", "Décision finale à valider manuellement par l’investisseur."),
        }
        if include_plan_amount:
            row["Montant de plan indicatif"] = idea.get("recommended_amount", 0.0)
        rows.append(row)
    return pd.DataFrame(rows)


def recommendations_frame(recommendations: list[dict[str, Any]]) -> pd.DataFrame:
    return investment_ideas_frame(recommendations)


def show_json_expander(label: str, value: Any) -> None:
    with st.expander(label):
        st.code(json.dumps(value, ensure_ascii=False, indent=2), language="json")
