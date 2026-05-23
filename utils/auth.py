from __future__ import annotations

import os
import secrets
from urllib.parse import urlencode

import requests
import streamlit as st

from database import initialize_user_defaults, upsert_google_user


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _hide_sidebar_before_auth() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="collapsedControl"] {
            display: none !important;
            visibility: hidden !important;
        }
        #MainMenu, footer {visibility: hidden;}
        .block-container {max-width: 920px; padding-top: 4rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _secret(name: str, default: str = "") -> str:
    env_name = f"GOOGLE_{name.upper()}"
    if os.getenv(env_name):
        return os.getenv(env_name, "")
    try:
        return str(st.secrets["google_oauth"].get(name, default))
    except Exception:
        return default


def _oauth_config() -> dict[str, str]:
    return {
        "client_id": _secret("client_id"),
        "client_secret": _secret("client_secret"),
        "redirect_uri": _secret("redirect_uri", "http://localhost:8501"),
    }


def _query_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _build_google_login_url(config: dict[str, str]) -> str:
    state = secrets.token_urlsafe(24)
    st.session_state["oauth_state"] = state
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def _exchange_code_for_profile(code: str, config: dict[str, str]) -> dict[str, str]:
    token_response = requests.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "redirect_uri": config["redirect_uri"],
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    token_response.raise_for_status()
    token_data = token_response.json()
    access_token = token_data["access_token"]

    user_response = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=20,
    )
    user_response.raise_for_status()
    return user_response.json()


def _handle_google_callback(config: dict[str, str]) -> None:
    code = _query_value("code")
    state = _query_value("state")
    error = _query_value("error")

    if error:
        st.error(f"Connexion Google annulee ou refusee: {error}")
        st.query_params.clear()
        return

    if not code:
        return

    expected_state = st.session_state.get("oauth_state")
    if expected_state and state != expected_state:
        st.error("Etat OAuth invalide. Relance la connexion Google.")
        st.query_params.clear()
        return

    with st.spinner("Connexion Google en cours..."):
        profile = _exchange_code_for_profile(code, config)
        user = upsert_google_user(profile)
        initialize_user_defaults(user["id"])
        st.session_state["authenticated"] = True
        st.session_state["user_id"] = user["id"]
        st.session_state["user"] = user
        st.session_state.pop("oauth_state", None)
    st.query_params.clear()
    st.rerun()


def require_login() -> None:
    if st.session_state.get("authenticated") and st.session_state.get("user_id"):
        return

    _hide_sidebar_before_auth()
    config = _oauth_config()
    missing_config = not config["client_id"] or not config["client_secret"]

    st.title("Connexion Google")
    st.caption("Connecte-toi avec ton compte Google pour ouvrir ton espace personnel.")

    left, middle, right = st.columns(3)
    left.metric("Local", "SQLite")
    middle.metric("Profils", "isoles")
    right.metric("Ordres", "jamais")

    st.info(
        "La premiere connexion cree automatiquement ton profil. "
        "Chaque compte Google dispose de ses propres parametres, watchlist, portefeuille, transactions et plans mensuels."
    )

    if missing_config:
        st.warning("OAuth Google n'est pas encore configure pour cette application locale.")
        st.markdown(
            """
            Ajoute un fichier `.streamlit/secrets.toml` local avec:

            ```toml
            [google_oauth]
            client_id = "TON_CLIENT_ID_GOOGLE"
            client_secret = "TON_CLIENT_SECRET_GOOGLE"
            redirect_uri = "http://localhost:8501"
            ```

            Dans Google Cloud Console, cree un client OAuth de type application Web et ajoute
            `http://localhost:8501` dans les URI de redirection autorises.
            """
        )
        st.stop()

    _handle_google_callback(config)
    login_url = _build_google_login_url(config)
    st.link_button("Continuer avec Google", login_url, use_container_width=True)
    st.caption("Aucun acces Gmail n'est demande: uniquement l'identite Google de base, l'email et le profil.")
    st.stop()


def render_logout_control() -> None:
    user = st.session_state.get("user", {})
    picture = user.get("picture_url") or user.get("picture")
    if picture:
        st.sidebar.image(picture, width=48)
    st.sidebar.caption(f"Connecte: {user.get('email', 'Compte Google')}")
    if st.sidebar.button("Se deconnecter"):
        for key in ["authenticated", "user_id", "user", "oauth_state"]:
            st.session_state.pop(key, None)
        st.rerun()
