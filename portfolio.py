from __future__ import annotations

from typing import Any

import pandas as pd

from database import get_assets, get_positions, load_settings
from market_data import fetch_many_market_data


def _target_allocations(settings: dict[str, Any]) -> dict[str, float]:
    return {
        "ETF": float(settings.get("target_allocation_etf", 0.70)),
        "ACTION": float(settings.get("target_allocation_stocks", 0.20)),
        "CASH": float(settings.get("target_allocation_cash", 0.10)),
    }


def enrich_positions_with_market(
    positions: pd.DataFrame | None = None,
    market_data: dict[str, dict[str, Any]] | None = None,
    force_market_refresh: bool = False,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    if positions is None:
        positions = get_positions()
    if positions.empty:
        return positions, market_data or {}

    positions = positions.copy()
    tickers = positions["ticker"].tolist()
    if market_data is None:
        market_data = fetch_many_market_data(tickers, force_refresh=force_market_refresh)

    current_prices = []
    market_status = []
    for _, row in positions.iterrows():
        data = market_data.get(row["ticker"], {})
        price = data.get("price")
        current_prices.append(price if price is not None else float(row["avg_buy_price"]))
        market_status.append(data.get("status", "missing"))

    positions["current_price"] = current_prices
    positions["market_status"] = market_status
    positions["current_value"] = positions["quantity"].astype(float) * positions["current_price"].astype(float)
    positions["unrealized_pnl"] = positions["current_value"] - positions["invested_amount"].astype(float)
    positions["unrealized_pnl_pct"] = positions["unrealized_pnl"] / positions["invested_amount"].replace(0, pd.NA).astype(float)
    return positions, market_data


def compute_portfolio_summary(
    settings: dict[str, Any] | None = None,
    market_data: dict[str, dict[str, Any]] | None = None,
    force_market_refresh: bool = False,
) -> dict[str, Any]:
    if settings is None:
        settings = load_settings()

    raw_positions = get_positions()
    positions, market_data = enrich_positions_with_market(raw_positions, market_data, force_market_refresh)
    assets = get_assets(active_only=False)
    if not positions.empty and not assets.empty:
        sector_map = assets.set_index("ticker")["sector"].to_dict()
        positions["sector"] = positions.apply(
            lambda row: row["sector"] if str(row.get("sector", "")).strip() else sector_map.get(row["ticker"], ""),
            axis=1,
        )

    cash = float(settings.get("cash_available", 0))
    positions_value = float(positions["current_value"].sum()) if not positions.empty else 0.0
    total_value = positions_value + cash
    invested = float(positions["invested_amount"].sum()) if not positions.empty else 0.0
    unrealized_pnl = float(positions["unrealized_pnl"].sum()) if not positions.empty else 0.0

    if total_value > 0 and not positions.empty:
        positions["weight"] = positions["current_value"] / total_value
    elif not positions.empty:
        positions["weight"] = 0.0

    allocation_current = {
        "ETF": float(positions.loc[positions["asset_type"] == "ETF", "current_value"].sum() / total_value) if total_value else 0.0,
        "ACTION": float(positions.loc[positions["asset_type"] == "ACTION", "current_value"].sum() / total_value) if total_value else 0.0,
        "CASH": float(cash / total_value) if total_value else 0.0,
    }
    allocation_target = _target_allocations(settings)
    allocation_gap = {
        bucket: allocation_target[bucket] - allocation_current.get(bucket, 0.0)
        for bucket in allocation_target
    }

    return {
        "positions": positions,
        "market_data": market_data,
        "cash": cash,
        "positions_value": positions_value,
        "total_value": total_value,
        "invested_amount": invested,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl / invested if invested else 0.0,
        "allocation_current": allocation_current,
        "allocation_target": allocation_target,
        "allocation_gap": allocation_gap,
        "currency": settings.get("base_currency", "EUR"),
        "currency_note": "Les conversions FX ne sont pas appliquees dans ce MVP; les montants sont suivis dans la devise de reference choisie.",
    }


def sector_exposure(summary: dict[str, Any]) -> pd.DataFrame:
    positions = summary.get("positions", pd.DataFrame())
    total = float(summary.get("total_value", 0))
    if positions.empty or total <= 0:
        return pd.DataFrame(columns=["sector", "current_value", "weight"])
    data = positions.copy()
    data["sector"] = data["sector"].fillna("").replace("", "Non renseigne")
    grouped = data.groupby("sector", as_index=False)["current_value"].sum()
    grouped["weight"] = grouped["current_value"] / total
    return grouped.sort_values("weight", ascending=False)


def position_value_map(summary: dict[str, Any]) -> dict[str, float]:
    positions = summary.get("positions", pd.DataFrame())
    if positions.empty:
        return {}
    return dict(zip(positions["ticker"], positions["current_value"]))


def position_weight_map(summary: dict[str, Any]) -> dict[str, float]:
    positions = summary.get("positions", pd.DataFrame())
    if positions.empty or "weight" not in positions:
        return {}
    return dict(zip(positions["ticker"], positions["weight"]))
