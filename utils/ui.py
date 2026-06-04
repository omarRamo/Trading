from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from database import initialize_database, load_settings, save_settings
from market_sync import (
    maybe_auto_sync_market_data,
    maybe_send_daily_recommendation_digest,
    sync_market_data,
)
from utils.auth import render_logout_control, require_login
from utils.formatting import format_currency, format_percent
from utils.i18n import (
    SUPPORTED_LANGUAGES,
    current_language,
    disclaimer_text,
    localized_page_title,
    set_language,
    t,
)
from utils.badges import signal_badge


def bootstrap_page(title: str) -> None:
    settings = load_settings()
    language = current_language(settings)
    translated_title = localized_page_title(title, language)
    sidebar_state = "expanded" if st.session_state.get("authenticated") else "collapsed"
    st.set_page_config(page_title=translated_title, layout="wide", initial_sidebar_state=sidebar_state)
    initialize_database()
    require_login()
    _render_language_selector(settings)
    render_logout_control()
    _render_market_sync_sidebar(translated_title)
    st.title(translated_title)
    st.caption(disclaimer_text(language))


def _render_language_selector(settings: dict[str, Any]) -> None:
    language = current_language(settings)
    options = list(SUPPORTED_LANGUAGES.keys())
    current_index = options.index(language) if language in options else 0
    selected = st.sidebar.selectbox(
        t("language", language),
        options,
        index=current_index,
        format_func=lambda code: SUPPORTED_LANGUAGES.get(code, code),
        key="language_selector",
    )
    if selected != language:
        set_language(selected)
        save_settings({"app_language": selected})
        st.rerun()


def _render_market_sync_sidebar(title: str) -> None:
    settings = load_settings()
    language = current_language(settings)
    st.sidebar.divider()
    st.sidebar.subheader(t("market_sync", language))
    if st.sidebar.button(t("sync_now", language), key=f"sync_{title}"):
        with st.spinner(t("sync_in_progress", language)):
            result = sync_market_data(force_refresh=True)
        st.sidebar.success(t("tickers_synced", language, count=result["synced"]))
        if result["errors"]:
            st.sidebar.warning(t("tickers_missing", language, count=len(result["errors"])))
        digest_result = maybe_send_daily_recommendation_digest(force=False)
        if digest_result:
            if digest_result.get("ok"):
                st.sidebar.success(t("digest_sent", language, count=digest_result.get("item_count", 0)))
            else:
                st.sidebar.warning(t("digest_failed", language, message=digest_result.get("message", "error")))
    else:
        with st.spinner(t("sync_check", language)):
            result = maybe_auto_sync_market_data()
        if result:
            st.sidebar.success(t("tickers_synced", language, count=result["synced"]))
            if result["errors"]:
                st.sidebar.warning(t("tickers_missing", language, count=len(result["errors"])))
        digest_result = maybe_send_daily_recommendation_digest(force=False)
        if digest_result:
            if digest_result.get("ok"):
                st.sidebar.success(t("digest_sent", language, count=digest_result.get("item_count", 0)))
            else:
                st.sidebar.warning(t("digest_failed", language, message=digest_result.get("message", "error")))

    refreshed_settings = load_settings()
    last_sync = refreshed_settings.get("last_market_sync_at") or t("never", language)
    auto_status = t("enabled", language) if refreshed_settings.get("auto_sync_market_data", True) else t("disabled", language)
    st.sidebar.caption(f"{t('auto_sync', language)} {auto_status}. {t('last_sync', language)}: {last_sync}")


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
    language = current_language(load_settings())
    currency = summary.get("currency", "EUR")
    pnl = summary.get("unrealized_pnl", 0.0)
    worst_gap = max((abs(v) for v in summary.get("allocation_gaps", {}).values()), default=0.0)
    worst_bucket = max(summary.get("allocation_gaps", {}).items(), key=lambda x: abs(x[1]), default=("N/A", 0.0))
    badge = "🔴" if worst_gap > 0.10 else "🟢"
    cards = st.columns(4)
    cards[0].metric(
        "Total value" if language == "en" else "Valeur totale",
        format_currency(summary["total_value"], currency),
        delta=("📈" if pnl > 0 else "📉"),
    )
    cards[1].metric(
        "Total unrealized P/L" if language == "en" else "P/L latent total",
        format_currency(pnl, currency),
        format_percent(summary.get("unrealized_pnl_pct", 0.0)),
    )
    cards[2].metric(
        "Most imbalanced allocation" if language == "en" else "Allocation la + déséquilibrée",
        f"{badge} {worst_bucket[0]}",
        format_percent(worst_bucket[1]),
    )
    cards[3].metric(
        "Available monthly budget" if language == "en" else "Enveloppe mensuelle dispo",
        format_currency(monthly_available if monthly_available is not None else summary.get("cash", 0.0), currency),
    )


def investment_ideas_frame(ideas: list[dict[str, Any]], include_plan_amount: bool = False) -> pd.DataFrame:
    language = current_language(load_settings())
    labels = {
        "ticker": "Ticker",
        "name": "Name" if language == "en" else "Nom",
        "asset_type": "Asset type" if language == "en" else "Type d'actif",
        "quality": "Quality score" if language == "en" else "Score de qualité",
        "signal": "Signal" if language == "en" else "Signal pédagogique",
        "risk": "Risk level" if language == "en" else "Niveau de risque",
        "max_amount": "Max theoretical amount" if language == "en" else "Montant maximum théorique",
        "reason": "Idea rationale" if language == "en" else "Raison de l'idée",
        "vigilance": "Risk points" if language == "en" else "Points de vigilance",
        "validation": "Validation" if language == "en" else "Validation",
        "plan_amount": "Planned amount" if language == "en" else "Montant de plan indicatif",
    }
    rows = []
    for idea in ideas:
        row = {
            labels["ticker"]: idea["ticker"],
            labels["name"]: idea.get("name", ""),
            labels["asset_type"]: idea["asset_type"],
            labels["quality"]: idea["score"],
            labels["signal"]: signal_badge(idea.get("prudence_level", "")),
            labels["risk"]: idea.get("risk_level", "unknown" if language == "en" else "inconnu"),
            labels["max_amount"]: idea.get("max_theoretical_amount", 0.0),
            labels["reason"]: idea.get("idea_reason") or " | ".join(idea.get("reasons", [])),
            labels["vigilance"]: " | ".join(idea.get("vigilance_points", [])),
            labels["validation"]: idea.get(
                "manual_decision",
                "Final decision requires manual validation by the investor."
                if language == "en"
                else "Décision finale à valider manuellement par l’investisseur.",
            ),
        }
        if include_plan_amount:
            row[labels["plan_amount"]] = idea.get("recommended_amount", 0.0)
        rows.append(row)
    return pd.DataFrame(rows)


def recommendations_frame(recommendations: list[dict[str, Any]]) -> pd.DataFrame:
    return investment_ideas_frame(recommendations)


def show_json_expander(label: str, value: Any) -> None:
    with st.expander(label):
        st.code(json.dumps(value, ensure_ascii=False, indent=2), language="json")
