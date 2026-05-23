from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from market_data import history_to_frame


def empty_figure(message: str = "Aucune donnee disponible") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def allocation_pie(allocation: dict[str, float], title: str) -> go.Figure:
    labels = list(allocation.keys())
    values = [allocation[label] for label in labels]
    fig = px.pie(names=labels, values=values, title=title, hole=0.45)
    fig.update_traces(textinfo="label+percent")
    fig.update_layout(height=340, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def allocation_gap_bar(current: dict[str, float], target: dict[str, float]) -> go.Figure:
    frame = pd.DataFrame(
        {
            "Poche": list(target.keys()),
            "Actuelle": [current.get(k, 0) for k in target],
            "Cible": [target[k] for k in target],
        }
    )
    melted = frame.melt(id_vars="Poche", var_name="Allocation", value_name="Poids")
    fig = px.bar(melted, x="Poche", y="Poids", color="Allocation", barmode="group", title="Allocation actuelle vs cible")
    fig.update_yaxes(tickformat=".0%")
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def price_chart(history, ticker: str) -> go.Figure:
    frame = history_to_frame(history)
    if frame.empty:
        return empty_figure(f"Aucune courbe disponible pour {ticker}")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=frame["date"], y=frame["close"], mode="lines", name="Prix"))
    if "ma50" in frame:
        fig.add_trace(go.Scatter(x=frame["date"], y=frame["ma50"], mode="lines", name="MM50"))
    if "ma200" in frame:
        fig.add_trace(go.Scatter(x=frame["date"], y=frame["ma200"], mode="lines", name="MM200"))
    fig.update_layout(title=f"{ticker} - prix et moyennes mobiles", height=420, margin=dict(l=20, r=20, t=50, b=20))
    return fig


def comparison_chart(histories: dict[str, list[dict]]) -> go.Figure:
    fig = go.Figure()
    traces = 0
    for ticker, history in histories.items():
        frame = history_to_frame(history)
        if frame.empty:
            continue
        first = frame["close"].dropna().iloc[0] if frame["close"].notna().any() else None
        if not first:
            continue
        frame["base_100"] = frame["close"] / first * 100
        fig.add_trace(go.Scatter(x=frame["date"], y=frame["base_100"], mode="lines", name=ticker))
        traces += 1
    if traces == 0:
        return empty_figure("Selection sans historique comparable")
    fig.update_layout(title="Comparaison base 100", height=430, margin=dict(l=20, r=20, t=50, b=20))
    fig.update_yaxes(title="Base 100")
    return fig


def backtest_chart(curve: pd.DataFrame) -> go.Figure:
    if curve.empty:
        return empty_figure("Backtest indisponible")
    fig = go.Figure()
    for col in [c for c in curve.columns if c not in {"Capital verse DCA", "Capital achat unique"}]:
        fig.add_trace(go.Scatter(x=curve.index, y=curve[col], mode="lines", name=col))
    if "Capital verse DCA" in curve:
        fig.add_trace(
            go.Scatter(
                x=curve.index,
                y=curve["Capital verse DCA"],
                mode="lines",
                name="Capital verse",
                line=dict(dash="dash"),
            )
        )
    fig.update_layout(title="Courbe de capital simulee", height=460, margin=dict(l=20, r=20, t=50, b=20))
    return fig
