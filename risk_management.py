from __future__ import annotations

from itertools import combinations
from typing import Any

import pandas as pd

from config import DEFAULT_SETTINGS
from market_data import history_to_frame
from portfolio import sector_exposure


def _alert(severity: str, title: str, message: str) -> dict[str, str]:
    return {"severity": severity, "title": title, "message": message}


def detect_leveraged_or_short_assets(positions: pd.DataFrame) -> list[str]:
    if positions.empty:
        return []
    keywords = ["3X", "2X", "LEVERAGED", "ULTRA", "SHORT", "BEAR", "INVERSE", "MARGIN"]
    flagged = []
    for _, row in positions.iterrows():
        text = f"{row.get('ticker', '')} {row.get('name', '')}".upper()
        if any(keyword in text for keyword in keywords):
            flagged.append(row["ticker"])
    return flagged


def concentration_alerts(summary: dict[str, Any], settings: dict[str, Any]) -> list[dict[str, str]]:
    positions = summary.get("positions", pd.DataFrame())
    if positions.empty:
        return []
    max_position = float(settings.get("max_individual_position", DEFAULT_SETTINGS["max_individual_position"]))
    hard_max = float(settings.get("hard_max_individual_position", DEFAULT_SETTINGS["hard_max_individual_position"]))
    alerts = []
    for _, row in positions[positions["asset_type"] == "ACTION"].iterrows():
        weight = float(row.get("weight", 0))
        if weight > hard_max:
            alerts.append(
                _alert(
                    "danger",
                    f"{row['ticker']} above 10%",
                    f"This stock is {weight:.1%} of portfolio value. Additional buys will be blocked by the engine.",
                )
            )
        elif weight > max_position:
            alerts.append(
                _alert(
                    "warning",
                    f"{row['ticker']} near the limit",
                    f"This stock is {weight:.1%}; configured personal limit: {max_position:.1%}.",
                )
            )
    return alerts


def cash_alerts(summary: dict[str, Any]) -> list[dict[str, str]]:
    current = summary["allocation_current"].get("CASH", 0.0)
    target = summary["allocation_target"].get("CASH", 0.10)
    if current < target - 0.02:
        return [
            _alert(
                "warning",
                "Cash below target",
                f"Current cash {current:.1%}, target {target:.1%}. Monthly plan will prioritize rebuilding cash.",
            )
        ]
    return []


def tech_exposure_alerts(summary: dict[str, Any], settings: dict[str, Any]) -> list[dict[str, str]]:
    exposure = sector_exposure(summary)
    if exposure.empty:
        return []
    tech_rows = exposure[exposure["sector"].str.contains("tech", case=False, na=False)]
    tech_weight = float(tech_rows["weight"].sum()) if not tech_rows.empty else 0.0
    limit = float(settings.get("tech_exposure_limit", DEFAULT_SETTINGS["tech_exposure_limit"]))
    if tech_weight > limit:
        return [
            _alert(
                "warning",
                "High tech exposure",
                f"Technology-classified assets represent {tech_weight:.1%}, above threshold {limit:.1%}.",
            )
        ]
    return []


def overbought_alerts(market_data: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    alerts = []
    for ticker, data in market_data.items():
        rsi = data.get("rsi14")
        if rsi is not None and rsi > 70:
            alerts.append(
                _alert(
                    "info",
                    f"{ticker} potentially overbought",
                    f"RSI 14 days at {rsi:.1f}. Engine applies a penalty to impulsive buys.",
                )
            )
    return alerts[:8]


def correlation_alerts(
    market_data: dict[str, dict[str, Any]],
    threshold: float = DEFAULT_SETTINGS["correlation_warning_threshold"],
) -> list[dict[str, str]]:
    frames = []
    for ticker, data in market_data.items():
        hist = history_to_frame(data.get("history", []))
        if hist.empty or len(hist) < 80:
            continue
        returns = hist.set_index("date")["close"].pct_change().dropna().tail(180)
        frames.append(returns.rename(ticker))
    if len(frames) < 2:
        return []
    returns_df = pd.concat(frames, axis=1).dropna(how="all")
    if returns_df.shape[1] < 2:
        return []
    corr = returns_df.corr()
    pairs = []
    for left, right in combinations(corr.columns, 2):
        value = corr.loc[left, right]
        if pd.notna(value) and value >= threshold:
            pairs.append((left, right, value))
    if not pairs:
        return []
    pairs = sorted(pairs, key=lambda item: item[2], reverse=True)[:5]
    examples = ", ".join(f"{a}/{b} ({v:.2f})" for a, b, v in pairs)
    return [
        _alert(
            "info",
            "Highly correlated assets",
            f"Some recent pairs are highly correlated: {examples}. Watch out for duplicated risk.",
        )
    ]


def generate_risk_alerts(summary: dict[str, Any], settings: dict[str, Any]) -> list[dict[str, str]]:
    positions = summary.get("positions", pd.DataFrame())
    market_data = summary.get("market_data", {})
    alerts: list[dict[str, str]] = []
    alerts.extend(concentration_alerts(summary, settings))
    alerts.extend(cash_alerts(summary))
    alerts.extend(tech_exposure_alerts(summary, settings))
    leveraged = detect_leveraged_or_short_assets(positions)
    if leveraged:
        alerts.append(
            _alert(
                "danger",
                "Incompatible instrument",
                "These positions look like leveraged, short, or inverse products: " + ", ".join(leveraged),
            )
        )
    alerts.extend(overbought_alerts(market_data))
    alerts.extend(correlation_alerts(market_data, float(settings.get("correlation_warning_threshold", 0.85))))
    if not alerts:
        alerts.append(
            _alert(
                "success",
                "No blocking alert",
                "Main MVP limits do not flag critical concentration or cash issues.",
            )
        )
    return alerts


def max_additional_amount_for_stock(
    ticker: str,
    summary: dict[str, Any],
    settings: dict[str, Any],
    monthly_amount: float = 0.0,
) -> float:
    positions = summary.get("positions", pd.DataFrame())
    total_after = float(summary.get("total_value", 0)) + float(monthly_amount)
    if total_after <= 0:
        return 0.0
    max_weight = min(
        float(settings.get("max_individual_position", 0.08)),
        float(settings.get("hard_max_individual_position", 0.10)),
    )
    current_value = 0.0
    if not positions.empty:
        match = positions[positions["ticker"] == ticker]
        if not match.empty:
            current_value = float(match.iloc[0]["current_value"])
    return max(0.0, max_weight * total_after - current_value)

