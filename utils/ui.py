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


def bootstrap_page(title: str) -> None:
    st.set_page_config(page_title=title, layout="wide")
    require_login()
    initialize_database()
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
    for alert in alerts:
        severity = alert.get("severity", "info")
        text = f"**{alert.get('title', 'Alerte')}**  \n{alert.get('message', '')}"
        if severity == "danger":
            st.error(text)
        elif severity == "warning":
            st.warning(text)
        elif severity == "success":
            st.success(text)
        else:
            st.info(text)


def metrics_row(summary: dict[str, Any]) -> None:
    currency = summary.get("currency", "EUR")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Valeur totale", format_currency(summary["total_value"], currency))
    col2.metric("Cash disponible", format_currency(summary["cash"], currency))
    col3.metric("P/L latent", format_currency(summary["unrealized_pnl"], currency), format_percent(summary["unrealized_pnl_pct"]))
    col4.metric("Valeur investie", format_currency(summary["positions_value"], currency))


def investment_ideas_frame(ideas: list[dict[str, Any]], include_plan_amount: bool = False) -> pd.DataFrame:
    rows = []
    for idea in ideas:
        row = {
            "Ticker": idea["ticker"],
            "Nom": idea.get("name", ""),
            "Type d'actif": idea["asset_type"],
            "Score de qualité": idea["score"],
            "Signal pédagogique": idea.get("prudence_level", ""),
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
