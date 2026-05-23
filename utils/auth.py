from __future__ import annotations

import streamlit as st

from config import ACCESS_PASSWORD, ACCESS_USERNAME


def require_login() -> None:
    if st.session_state.get("authenticated"):
        return

    st.title("Acces protege")
    st.caption("Cette application contient des donnees personnelles de portefeuille local.")

    with st.form("login_form"):
        username = st.text_input("Utilisateur")
        password = st.text_input("Mot de passe", type="password")
        submitted = st.form_submit_button("Se connecter")

    if submitted:
        if username == ACCESS_USERNAME and password == ACCESS_PASSWORD:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Identifiants incorrects.")

    st.stop()


def render_logout_control() -> None:
    st.sidebar.caption(f"Connecte: {st.session_state.get('username', ACCESS_USERNAME)}")
    if st.sidebar.button("Se deconnecter"):
        st.session_state.pop("authenticated", None)
        st.session_state.pop("username", None)
        st.rerun()
