from __future__ import annotations

from datetime import date

import streamlit as st

import charts as charts_lib
import database as db
from database import (
    add_transaction,
    get_assets,
    get_transactions,
    load_settings,
)
from utils.formatting import format_percent
from utils.ui import bootstrap_page


bootstrap_page("Transactions")

settings = load_settings()
trade_journal_r_chart = getattr(charts_lib, "trade_journal_r_chart", None)
add_trade_journal_entry = getattr(db, "add_trade_journal_entry", None)
get_trade_journal_entries = getattr(db, "get_trade_journal_entries", None)
trade_journal_stats = getattr(db, "trade_journal_stats", None)
update_trade_journal_entry = getattr(db, "update_trade_journal_entry", None)

st.subheader("Calculateur de taille de position")
calc_col1, calc_col2, calc_col3, calc_col4 = st.columns(4)
with calc_col1:
    calc_direction = st.selectbox("Direction", ["LONG", "SHORT"], key="calc_direction")
with calc_col2:
    calc_entry = st.number_input("Prix d'entree", min_value=0.0, value=100.0, step=0.1, key="calc_entry")
with calc_col3:
    calc_stop = st.number_input("Stop loss", min_value=0.0, value=95.0, step=0.1, key="calc_stop")
with calc_col4:
    calc_rr = st.number_input(
        "R/R cible",
        min_value=0.5,
        max_value=10.0,
        value=float(settings.get("default_rr_target", 2.0)),
        step=0.1,
        key="calc_rr",
    )

calc_col5, calc_col6 = st.columns(2)
with calc_col5:
    calc_account = st.number_input(
        "Capital de reference",
        min_value=0.0,
        value=float(settings.get("capital_total", 0.0)),
        step=100.0,
        key="calc_account",
    )
with calc_col6:
    calc_risk_pct = st.number_input(
        "Risque par trade (%)",
        min_value=0.1,
        max_value=5.0,
        value=float(settings.get("risk_per_trade_pct", 0.01)) * 100,
        step=0.1,
        key="calc_risk_pct",
    )

risk_per_unit = abs(calc_entry - calc_stop)
risk_budget = calc_account * (calc_risk_pct / 100)
position_qty = risk_budget / risk_per_unit if risk_per_unit > 0 else 0.0
position_notional = position_qty * calc_entry
if calc_direction == "LONG":
    target_price = calc_entry + calc_rr * risk_per_unit
else:
    target_price = calc_entry - calc_rr * risk_per_unit

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("Budget risque", f"{risk_budget:,.2f}")
metric_col2.metric("Risque/unite", f"{risk_per_unit:,.4f}")
metric_col3.metric("Taille theorique", f"{position_qty:,.2f}")
metric_col4.metric("Notional theorique", f"{position_notional:,.2f}")
st.caption(f"Target theorique ({calc_direction}): {target_price:,.4f}")

assets = get_assets(active_only=True)
choices = ["Saisie manuelle"] + assets["ticker"].tolist()
selected = st.selectbox("Actif", choices)
defaults = {}
if selected != "Saisie manuelle":
    defaults = assets[assets["ticker"] == selected].iloc[0].to_dict()

with st.form("transaction_form"):
    ticker = st.text_input("Ticker", value=defaults.get("ticker", ""))
    asset_name = st.text_input("Nom", value=defaults.get("name", ""))
    asset_type = st.selectbox("Type", ["ETF", "ACTION"], index=0 if defaults.get("asset_type", "ETF") == "ETF" else 1)
    transaction_type = st.selectbox("Operation", ["BUY", "SELL"])
    quantity = st.number_input("Quantite", min_value=0.0, value=0.0, step=0.01)
    price = st.number_input("Prix", min_value=0.0, value=0.0, step=0.01)
    transaction_date = st.date_input("Date", value=date.today())
    currency = st.text_input("Devise", value=defaults.get("currency", settings.get("base_currency", "EUR")))
    fees = st.number_input("Frais", min_value=0.0, value=0.0, step=0.1)
    notes = st.text_area("Notes")
    update_position = st.checkbox("Mettre a jour la position si achat", value=True)
    submitted = st.form_submit_button("Enregistrer la transaction")

if submitted:
    if not ticker.strip() or quantity <= 0 or price <= 0:
        st.error("Ticker, quantite et prix sont obligatoires.")
    else:
        add_transaction(
            {
                "ticker": ticker,
                "asset_name": asset_name or ticker,
                "asset_type": asset_type,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "price": price,
                "transaction_date": transaction_date.isoformat(),
                "currency": currency.upper().strip() or settings.get("base_currency", "EUR"),
                "fees": fees,
                "amount": quantity * price + fees,
                "notes": notes,
            },
            update_position=update_position,
        )
        st.success("Transaction enregistree localement.")
        st.rerun()

st.subheader("Historique local")
transactions = get_transactions()
if transactions.empty:
    st.info("Aucune transaction enregistree.")
else:
    st.dataframe(transactions, use_container_width=True, hide_index=True)

st.subheader("Journal de trades")
with st.form("trade_journal_form"):
    jcol1, jcol2, jcol3 = st.columns(3)
    with jcol1:
        j_ticker = st.text_input("Ticker journal", value=defaults.get("ticker", ""))
    with jcol2:
        j_direction = st.selectbox("Direction setup", ["LONG", "SHORT"])
    with jcol3:
        j_setup = st.text_input("Setup tag", placeholder="breakout, pullback, mean-reversion")

    jcol4, jcol5, jcol6 = st.columns(3)
    with jcol4:
        j_entry = st.number_input("Entry setup", min_value=0.0, value=float(calc_entry), step=0.1)
    with jcol5:
        j_stop = st.number_input("Stop setup", min_value=0.0, value=float(calc_stop), step=0.1)
    with jcol6:
        j_target = st.number_input("Target setup", min_value=0.0, value=float(target_price), step=0.1)

    jcol7, jcol8 = st.columns(2)
    with jcol7:
        j_risk_amount = st.number_input("Risque monetaire", min_value=0.0, value=float(risk_budget), step=1.0)
    with jcol8:
        j_planned_rr = st.number_input("R/R planifie", min_value=0.0, value=float(calc_rr), step=0.1)

    j_thesis = st.text_area("These")
    j_invalidation = st.text_area("Invalidation")
    j_notes = st.text_area("Notes journal")
    journal_submit = st.form_submit_button("Ajouter au journal")

if journal_submit:
    if not callable(add_trade_journal_entry):
        st.warning("Journal de trades non disponible dans cette version. Mise a jour necessaire.")
    elif not j_ticker.strip() or not j_setup.strip():
        st.error("Ticker et setup tag sont obligatoires pour le journal.")
    else:
        add_trade_journal_entry(
            {
                "ticker": j_ticker,
                "direction": j_direction,
                "setup_tag": j_setup,
                "thesis": j_thesis,
                "invalidation": j_invalidation,
                "entry_price": j_entry,
                "stop_loss": j_stop,
                "target_price": j_target,
                "risk_amount": j_risk_amount,
                "planned_rr": j_planned_rr,
                "status": "open",
                "opened_at": date.today().isoformat(),
                "notes": j_notes,
            }
        )
        st.success("Entree de journal ajoutee.")
        st.rerun()

journal_entries = get_trade_journal_entries() if callable(get_trade_journal_entries) else None
if journal_entries is None:
    journal_entries = get_transactions().head(0)
stats = (
    trade_journal_stats()
    if callable(trade_journal_stats)
    else {"total": 0, "open": 0, "win_rate": 0.0, "expectancy_r": 0.0}
)
stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
stat_col1.metric("Trades journal", stats["total"])
stat_col2.metric("Trades ouverts", stats["open"])
stat_col3.metric("Win rate (R>0)", format_percent(stats["win_rate"]))
stat_col4.metric("Expectancy (R)", f"{stats['expectancy_r']:.2f}")

if not journal_entries.empty:
    with st.expander("Clore un trade"):
        open_entries = journal_entries[journal_entries["status"] == "open"]
        if open_entries.empty:
            st.info("Aucun trade ouvert a clore.")
        else:
            row_labels = [
                f"#{int(row['id'])} {row['ticker']} {row['setup_tag']}"
                for _, row in open_entries.iterrows()
            ]
            selected_label = st.selectbox("Trade ouvert", row_labels)
            selected_id = int(selected_label.split(" ")[0].replace("#", ""))
            close_col1, close_col2, close_col3 = st.columns(3)
            with close_col1:
                realized_pnl = st.number_input("P/L realise", value=0.0, step=1.0)
            with close_col2:
                realized_r = st.number_input("R realise", value=0.0, step=0.1)
            with close_col3:
                close_date = st.date_input("Date de cloture", value=date.today())
            if st.button("Valider cloture"):
                if callable(update_trade_journal_entry):
                    update_trade_journal_entry(
                        selected_id,
                        {
                            "status": "closed",
                            "realized_pnl": realized_pnl,
                            "realized_r": realized_r,
                            "closed_at": close_date.isoformat(),
                        },
                    )
                    st.success("Trade clos dans le journal.")
                    st.rerun()
                else:
                    st.warning("Fonction de cloture non disponible dans cette version.")

    if callable(trade_journal_r_chart):
        st.plotly_chart(trade_journal_r_chart(journal_entries), use_container_width=True)
    else:
        st.info("Graphique R indisponible sur cette version. Mets a jour charts.py.")
    st.dataframe(journal_entries, use_container_width=True, hide_index=True)
else:
    st.info("Aucune entree de journal pour le moment.")
