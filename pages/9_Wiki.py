from __future__ import annotations

import streamlit as st

from utils.ui import bootstrap_page


bootstrap_page("Wiki")

st.info(
    "Cette page explique les notions de l'application. Elle reste pedagogique et ne constitue pas un conseil financier."
)

st.subheader("Dashboard")
st.write(
    "Le Dashboard regroupe la valeur du portefeuille, le cash, l'allocation actuelle, "
    "l'allocation cible, les alertes et les meilleurs candidats a analyser."
)

st.subheader("Portefeuille")
st.write(
    "Le portefeuille est saisi manuellement. Il sert a calculer les poids, les plus-values latentes, "
    "les ecarts d'allocation et les limites de concentration. Une suppression locale ne modifie rien sur Revolut."
)

st.subheader("Marches")
st.write(
    "La page Marches recupere les prix via yfinance, calcule les performances recentes, MM50, MM200, RSI, "
    "volatilite et volume moyen. Si un ticker ne repond pas, les autres continuent de fonctionner."
)

st.subheader("Plan mensuel")
st.write(
    "Le plan mensuel transforme ton enveloppe en repartition indicative. Il augmente les poches sous-ponderees, "
    "reconstitue le cash si necessaire et bloque les actions trop concentrees."
)

st.subheader("Idees d'investissement")
st.write(
    "Les idees sont des candidats a analyser. Le score va de 0 a 100 et les signaux restent simples: "
    "interessant, a surveiller, attendre, eviter. La decision finale reste manuelle."
)

st.subheader("Backtest")
st.write(
    "Le backtest compare des scenarios historiques simples: DCA ETF, allocation 70/20/10 et achat unique au depart. "
    "Il ignore fiscalite, frais detailles, change et disponibilite exacte Revolut."
)

st.subheader("RSI, MM50, MM200")
st.write(
    "Le RSI mesure une situation de surachat ou de faiblesse recente. MM50 et MM200 sont des moyennes mobiles: "
    "elles aident a visualiser la tendance, sans predire l'avenir."
)

st.subheader("Risque et concentration")
st.write(
    "Les actions individuelles sont plafonnees entre 5 % et 10 % selon ton reglage. Les ETF peuvent avoir un poids "
    "plus important, mais l'application signale les concentrations sectorielles et les correlations elevees."
)

st.subheader("Profils Google")
st.write(
    "Chaque compte Google cree un profil local distinct dans SQLite. Les donnees ne sont pas melangees entre utilisateurs."
)
