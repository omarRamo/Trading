from __future__ import annotations

import os
import re
import secrets
from urllib.parse import urlencode

import requests
import streamlit as st

from database import authenticate_email_user, create_email_user, initialize_user_defaults, upsert_google_user
from utils.i18n import current_language, t


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
        st.error(f"Google sign-in cancelled or denied: {error}")
        st.query_params.clear()
        return

    if not code:
        return

    expected_state = st.session_state.get("oauth_state")
    if expected_state and state != expected_state:
        st.error("Invalid OAuth state. Retry Google sign-in.")
        st.query_params.clear()
        return

    with st.spinner("Signing in with Google..."):
        profile = _exchange_code_for_profile(code, config)
        user = upsert_google_user(profile)
        initialize_user_defaults(user["id"])
        st.session_state["authenticated"] = True
        st.session_state["user_id"] = user["id"]
        st.session_state["user"] = user
        st.session_state.pop("oauth_state", None)
    st.query_params.clear()
    st.rerun()


def _start_user_session(user: dict[str, str]) -> None:
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["user"] = user
    st.session_state.pop("oauth_state", None)


def _render_email_login() -> None:
    language = current_language({})
    with st.form("email_login_form"):
        email = st.text_input(t("email_or_username", language), placeholder="omar or omar@example.com")
        password = st.text_input(t("password", language), type="password")
        submitted = st.form_submit_button(t("login", language), use_container_width=True)

    if not submitted:
        return
    attempts = int(st.session_state.get("login_attempts", 0))
    if attempts >= 5:
        st.error("Too many sign-in attempts (max 5). Reload the page.")
        return
    user = authenticate_email_user(email, password)
    if user is None:
        st.session_state["login_attempts"] = attempts + 1
        st.error("Invalid username or password.")
        return
    st.session_state["login_attempts"] = 0
    _start_user_session(user)
    st.success("Sign-in successful.")
    st.rerun()


def _render_account_creation() -> None:
    language = current_language({})
    with st.form("email_signup_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input(t("first_name", language))
        with col2:
            last_name = st.text_input(t("last_name", language))
        email = st.text_input(t("email_or_username", language), placeholder="omar@example.com")
        password = st.text_input(t("password", language), type="password")
        password_confirm = st.text_input(t("confirm_password", language), type="password")
        accepted = st.checkbox("I understand that my data remains local and ideas are not orders.")
        submitted = st.form_submit_button(t("create_account", language), use_container_width=True)

    if not submitted:
        return
    if not first_name.strip() or not last_name.strip():
        st.error("First name and last name are required.")
        return
    if not EMAIL_PATTERN.match(email.strip()):
        st.error("Invalid email.")
        return
    if len(password) < 8:
        st.error("Password must contain at least 8 characters.")
        return
    if password != password_confirm:
        st.error("Passwords do not match.")
        return
    if not accepted:
        st.error("Confirm usage rule before creating the account.")
        return

    try:
        user = create_email_user(email, password, first_name, last_name)
    except ValueError as exc:
        st.error(str(exc))
        return
    _start_user_session(user)
    st.success("Account created. Welcome.")
    st.rerun()


def _render_google_login(config: dict[str, str], missing_config: bool) -> None:
    language = current_language({})
    if missing_config:
        st.warning("Google OAuth is not configured yet for this local app.")
        with st.expander("Configure Google OAuth"):
            st.markdown(
                """
                Add a local `.streamlit/secrets.toml` file with:

                ```toml
                [google_oauth]
                client_id = "TON_CLIENT_ID_GOOGLE"
                client_secret = "TON_CLIENT_SECRET_GOOGLE"
                redirect_uri = "http://localhost:8501"
                ```

                In Google Cloud Console, create a Web application OAuth client and add
                `http://localhost:8501` to authorized redirect URIs.
                """
            )
        return

    login_url = _build_google_login_url(config)
    st.link_button(f"{t('login', language)} Google", login_url, use_container_width=True)
    st.caption("No Gmail mailbox access is requested: only basic Google identity, email, and profile.")


def require_login() -> None:
    if st.session_state.get("authenticated") and st.session_state.get("user_id"):
        return

    _hide_sidebar_before_auth()
    config = _oauth_config()
    missing_config = not config["client_id"] or not config["client_secret"]

    # Login screen stays in default English; language can be changed after sign-in.
    language = "en"

    if not missing_config:
        _handle_google_callback(config)

    st.title(t("sign_in", language))
    st.caption(t("open_workspace", language))

    left, middle, right = st.columns(3)
    left.metric("Local", "SQLite")
    middle.metric(t("profiles", language), t("isolated", language))
    right.metric(t("orders", language), t("never_label", language))

    st.info(
        "Each account has isolated settings, watchlist, portfolio, transactions, and monthly plans. "
        "You can use a local email/password account or Google if OAuth is configured."
    )
    st.caption("Demo account: username omar, password admin.")

    login_tab, signup_tab, google_tab = st.tabs([t("login", language), t("create_account", language), t("google", language)])
    with login_tab:
        _render_email_login()
    with signup_tab:
        _render_account_creation()
    with google_tab:
        _render_google_login(config, missing_config)
    st.stop()


def render_logout_control() -> None:
    language = current_language({})
    user = st.session_state.get("user", {})
    picture = user.get("picture_url") or user.get("picture")
    if picture:
        st.sidebar.image(picture, width=48)
    st.sidebar.caption(t("connected_as", language, email=user.get("email", "Google account")))
    if st.sidebar.button(t("sign_out", language)):
        for key in ["authenticated", "user_id", "user", "oauth_state"]:
            st.session_state.pop(key, None)
        st.rerun()
