from __future__ import annotations

from typing import Any

import streamlit as st

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "fr": "Français",
}

PAGE_TITLES: dict[str, dict[str, str]] = {
    "Dashboard": {"en": "Dashboard", "fr": "Dashboard"},
    "Portefeuille": {"en": "Portfolio", "fr": "Portefeuille"},
    "Marches": {"en": "Markets", "fr": "Marches"},
    "Plan mensuel": {"en": "Monthly Plan", "fr": "Plan mensuel"},
    "Idées d'investissement": {"en": "Investment Ideas", "fr": "Idées d'investissement"},
    "Backtest": {"en": "Backtest", "fr": "Backtest"},
    "Parametres": {"en": "Settings", "fr": "Parametres"},
    "Transactions": {"en": "Transactions", "fr": "Transactions"},
    "Profil": {"en": "Profile", "fr": "Profil"},
    "Wiki": {"en": "Wiki", "fr": "Wiki"},
    "Connexion": {"en": "Sign In", "fr": "Connexion"},
}

TRANSLATIONS: dict[str, dict[str, str]] = {
    "language": {"en": "Language", "fr": "Langue"},
    "market_sync": {"en": "Market Sync", "fr": "Synchro marche"},
    "sync_now": {"en": "Sync now", "fr": "Synchroniser maintenant"},
    "sync_in_progress": {"en": "Syncing market data...", "fr": "Synchronisation des donnees de marche..."},
    "sync_check": {"en": "Checking market sync...", "fr": "Verification de la synchro marche..."},
    "tickers_synced": {"en": "{count} tickers synced.", "fr": "{count} tickers synchronises."},
    "tickers_missing": {"en": "{count} ticker(s) without data.", "fr": "{count} ticker(s) sans donnees."},
    "auto_sync": {"en": "Auto-sync", "fr": "Auto-sync"},
    "enabled": {"en": "enabled", "fr": "active"},
    "disabled": {"en": "disabled", "fr": "desactivee"},
    "last_sync": {"en": "Last sync", "fr": "Derniere synchro"},
    "never": {"en": "Never", "fr": "Jamais"},
    "digest_sent": {"en": "Email digest sent ({count} idea(s)).", "fr": "Digest email envoye ({count} idee(s))."},
    "digest_failed": {"en": "Email digest not sent: {message}.", "fr": "Digest email non envoye: {message}."},
    "connected_as": {"en": "Signed in: {email}", "fr": "Connecte: {email}"},
    "sign_out": {"en": "Sign out", "fr": "Se deconnecter"},
    "sign_in": {"en": "Sign In", "fr": "Connexion"},
    "open_workspace": {"en": "Open your personal workspace or create a local profile.", "fr": "Ouvre ton espace personnel ou cree un profil local."},
    "profiles": {"en": "Profiles", "fr": "Profils"},
    "isolated": {"en": "isolated", "fr": "isoles"},
    "orders": {"en": "Orders", "fr": "Ordres"},
    "never_label": {"en": "never", "fr": "jamais"},
    "email_or_username": {"en": "Email or username", "fr": "Email ou identifiant"},
    "password": {"en": "Password", "fr": "Mot de passe"},
    "login": {"en": "Sign in", "fr": "Se connecter"},
    "create_account": {"en": "Create account", "fr": "Creer mon compte"},
    "first_name": {"en": "First name", "fr": "Prenom"},
    "last_name": {"en": "Last name", "fr": "Nom"},
    "confirm_password": {"en": "Confirm password", "fr": "Confirmer le mot de passe"},
    "google": {"en": "Google", "fr": "Google"},
}


def normalize_language(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    if candidate not in SUPPORTED_LANGUAGES:
        return "en"
    return candidate


def current_language(settings: dict[str, Any] | None = None) -> str:
    if "app_language" in st.session_state:
        return normalize_language(st.session_state.get("app_language"))
    from_settings = normalize_language((settings or {}).get("app_language", "en"))
    st.session_state["app_language"] = from_settings
    return from_settings


def set_language(language: str) -> None:
    st.session_state["app_language"] = normalize_language(language)


def t(key: str, language: str | None = None, **kwargs: Any) -> str:
    language = normalize_language(language or st.session_state.get("app_language", "en"))
    values = TRANSLATIONS.get(key)
    if not values:
        return key
    text = values.get(language) or values.get("en") or key
    try:
        return text.format(**kwargs)
    except Exception:
        return text


def localized_page_title(title: str, language: str | None = None) -> str:
    language = normalize_language(language or st.session_state.get("app_language", "en"))
    mapping = PAGE_TITLES.get(title)
    if not mapping:
        return title
    return mapping.get(language, title)


def disclaimer_text(language: str | None = None) -> str:
    language = normalize_language(language or st.session_state.get("app_language", "en"))
    if language == "fr":
        return (
            "Compagnon local d'aide a la decision pour une construction patrimoniale long terme. "
            "Les idees affichees sont des signaux pedagogiques incertains, jamais des ordres d'achat ou de vente. "
            "Aucun ordre n'est transmis a Revolut, aucun levier, aucune marge et aucune vente a decouvert ne sont utilises. "
            "Décision finale à valider manuellement par l’investisseur."
        )
    return (
        "Local decision-support companion for long-term portfolio building. "
        "Displayed ideas are educational and uncertain signals, never buy/sell orders. "
        "No order is sent to Revolut, no leverage, no margin, and no short selling are used. "
        "Final investment decision always requires manual validation."
    )
