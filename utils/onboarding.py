from __future__ import annotations

import streamlit as st

from database import get_positions, save_settings, seed_demo_portfolio


def show_onboarding_if_needed(settings: dict) -> None:
    flag = bool(settings.get("onboarding_completed", False))
    empty_portfolio = get_positions().empty
    if flag or not empty_portfolio:
        return

    with st.expander("Bienvenue — 3 étapes pour démarrer", expanded=True):
        st.markdown("**Étape 1** · Définir votre enveloppe mensuelle")
        monthly = st.number_input(
            "Enveloppe mensuelle (€)",
            min_value=0.0,
            step=50.0,
            value=float(settings.get("monthly_investment", 1000)),
            key="onboarding_monthly",
        )
        if st.button("Enregistrer l'enveloppe", key="onboarding_save_monthly"):
            save_settings({"monthly_investment": monthly})
            st.success("Enveloppe mensuelle enregistrée.")

        st.markdown("**Étape 2** · Initialiser votre portefeuille")
        col1, col2 = st.columns(2)
        if col1.button("Charger le portefeuille fictif", key="onboarding_demo"):
            seed_demo_portfolio(overwrite=False)
            st.success("Portefeuille fictif chargé.")
        col2.caption("Ou allez dans Portefeuille pour saisir votre 1ère position.")

        st.markdown("**Étape 3** · Lancer la première analyse")
        if st.button("Terminer l'onboarding", key="onboarding_done"):
            save_settings({"onboarding_completed": True})
            st.success("Parfait, onboarding terminé.")
            st.rerun()
