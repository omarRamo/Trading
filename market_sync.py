from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from database import get_assets, load_settings, save_settings
from market_data import fetch_many_market_data


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def market_sync_due(settings: dict[str, Any] | None = None) -> bool:
    settings = settings or load_settings()
    if not bool(settings.get("auto_sync_market_data", True)):
        return False
    last_sync = _parse_datetime(settings.get("last_market_sync_at"))
    if last_sync is None:
        return True
    interval_hours = float(settings.get("auto_sync_interval_hours", 6))
    return datetime.now(timezone.utc) - last_sync >= timedelta(hours=interval_hours)


def sync_market_data(force_refresh: bool = False) -> dict[str, Any]:
    assets = get_assets(active_only=True)
    tickers = assets["ticker"].tolist() if not assets.empty else []
    if not tickers:
        return {"synced": 0, "errors": [], "tickers": [], "finished_at": ""}

    results = fetch_many_market_data(tickers, force_refresh=force_refresh)
    errors = [
        f"{ticker}: {data.get('error')}"
        for ticker, data in results.items()
        if data.get("status") == "error"
    ]
    finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_settings({"last_market_sync_at": finished_at})
    return {
        "synced": len(results),
        "errors": errors,
        "tickers": list(results.keys()),
        "finished_at": finished_at,
    }


def maybe_auto_sync_market_data() -> dict[str, Any] | None:
    settings = load_settings()
    if not market_sync_due(settings):
        return None
    return sync_market_data(force_refresh=False)
