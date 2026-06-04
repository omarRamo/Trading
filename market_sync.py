from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from database import (
    get_assets,
    get_notification_preferences,
    load_settings,
    log_notification_delivery,
    save_settings,
    set_notification_last_sent,
)
from email_notifications import send_recommendations_digest
from market_data import fetch_many_market_data
from strategy import generate_recommendations


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


def _notification_due(preferences: dict[str, Any], now_utc: datetime | None = None) -> bool:
    if not preferences.get("is_enabled"):
        return False
    if str(preferences.get("frequency", "manual")).lower() != "daily":
        return False
    if not str(preferences.get("email", "")).strip():
        return False

    now_utc = now_utc or datetime.now(timezone.utc)
    send_hour_utc = int(preferences.get("send_hour_utc", 7))
    if now_utc.hour < send_hour_utc:
        return False

    last_sent = _parse_datetime(preferences.get("last_sent_at"))
    if last_sent is None:
        return True
    return last_sent.date() < now_utc.date()


def maybe_send_daily_recommendation_digest(force: bool = False) -> dict[str, Any] | None:
    preferences = get_notification_preferences()
    if not force and not _notification_due(preferences):
        return None

    recommendations, summary = generate_recommendations(force_market_refresh=False, persist=False)
    result = send_recommendations_digest(
        recommendations=recommendations,
        summary=summary,
        preferences=preferences,
        target_email=str(preferences.get("email", "")),
    )
    status = "sent" if result.ok else "error"
    log_notification_delivery(
        email=str(preferences.get("email", "")).strip(),
        subject=result.subject or "Trading Digest",
        status=status,
        item_count=result.item_count,
        error_message="" if result.ok else result.message,
    )
    if result.ok:
        set_notification_last_sent()

    return {
        "ok": result.ok,
        "message": result.message,
        "item_count": result.item_count,
        "subject": result.subject,
    }
