from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from config import CACHE_TTL_HOURS
from database import get_market_cache, upsert_market_cache


def _clean_number(value: Any) -> float | None:
    try:
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def _cache_is_fresh(cache: dict[str, Any] | None) -> bool:
    if not cache:
        return False
    try:
        fetched_at = datetime.fromisoformat(cache["fetched_at"])
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - fetched_at < timedelta(hours=CACHE_TTL_HOURS)
    except (KeyError, TypeError, ValueError):
        return False


def calculate_rsi(close: pd.Series, window: int = 14) -> float | None:
    if close.empty or len(close) < window + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    if avg_loss.iloc[-1] == 0:
        return 100.0
    rs = avg_gain.iloc[-1] / avg_loss.iloc[-1]
    return _clean_number(100 - (100 / (1 + rs)))


def _pct_change(close: pd.Series, sessions: int) -> float | None:
    if len(close) <= sessions:
        return None
    start = close.iloc[-sessions - 1]
    end = close.iloc[-1]
    if start == 0 or pd.isna(start) or pd.isna(end):
        return None
    return _clean_number(end / start - 1)


def _normalise_yfinance_history(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw.empty:
        return raw
    hist = raw.copy()
    if isinstance(hist.columns, pd.MultiIndex):
        last_level = hist.columns.get_level_values(-1)
        first_level = hist.columns.get_level_values(0)
        if ticker in last_level:
            hist = hist.xs(ticker, axis=1, level=-1)
        elif ticker in first_level:
            hist = hist.xs(ticker, axis=1, level=0)
        else:
            hist.columns = hist.columns.get_level_values(0)
    return hist


def _download_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("Le package yfinance n'est pas installe.") from exc

    raw = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    hist = _normalise_yfinance_history(raw, ticker)
    if hist.empty:
        return hist
    hist = hist.sort_index()
    if "Adj Close" in hist.columns and hist["Adj Close"].notna().any():
        hist["close"] = hist["Adj Close"]
    elif "Close" in hist.columns:
        hist["close"] = hist["Close"]
    else:
        return pd.DataFrame()
    hist["volume"] = hist["Volume"] if "Volume" in hist.columns else np.nan
    hist = hist[["close", "volume"]].dropna(subset=["close"])
    return hist


def _metrics_from_history(hist: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    close = hist["close"].dropna()
    returns = close.pct_change().dropna()
    ma50_series = close.rolling(50).mean()
    ma200_series = close.rolling(200).mean()
    price = close.iloc[-1] if not close.empty else None
    previous_close = close.iloc[-2] if len(close) > 1 else None

    history = pd.DataFrame(
        {
            "date": hist.index.strftime("%Y-%m-%d"),
            "close": close,
            "ma50": ma50_series,
            "ma200": ma200_series,
            "volume": hist["volume"],
        }
    )
    history_rows = [
        {
            "date": row["date"],
            "close": _clean_number(row["close"]),
            "ma50": _clean_number(row["ma50"]),
            "ma200": _clean_number(row["ma200"]),
            "volume": _clean_number(row["volume"]),
        }
        for _, row in history.tail(520).iterrows()
    ]

    metrics = {
        "price": _clean_number(price),
        "previous_close": _clean_number(previous_close),
        "change_1d": _clean_number(price / previous_close - 1) if previous_close not in (None, 0) else None,
        "perf_1m": _pct_change(close, 21),
        "perf_3m": _pct_change(close, 63),
        "perf_6m": _pct_change(close, 126),
        "perf_1y": _pct_change(close, 252),
        "ma50": _clean_number(ma50_series.iloc[-1]) if len(ma50_series) else None,
        "ma200": _clean_number(ma200_series.iloc[-1]) if len(ma200_series) else None,
        "rsi14": calculate_rsi(close),
        "volatility": _clean_number(returns.tail(63).std() * np.sqrt(252)) if not returns.empty else None,
        "avg_volume": _clean_number(hist["volume"].tail(30).mean()),
        "status": "ok",
        "error": None,
    }
    return metrics, history_rows


def fetch_market_data(ticker: str, period: str = "2y", force_refresh: bool = False) -> dict[str, Any]:
    ticker = ticker.upper().strip()
    cache = get_market_cache(ticker)
    if cache and not force_refresh and _cache_is_fresh(cache):
        cache["from_cache"] = True
        return cache

    try:
        hist = _download_history(ticker, period=period)
        if hist.empty:
            raise RuntimeError("Aucune donnee de marche disponible.")
        metrics, history_rows = _metrics_from_history(hist)
        upsert_market_cache(ticker, metrics, history_rows)
        return {"ticker": ticker, "history": history_rows, "from_cache": False, **metrics}
    except Exception as exc:
        if cache:
            cache["from_cache"] = True
            cache["status"] = "stale"
            cache["error"] = f"Donnees conservees depuis le cache: {exc}"
            return cache
        return {
            "ticker": ticker,
            "price": None,
            "previous_close": None,
            "change_1d": None,
            "perf_1m": None,
            "perf_3m": None,
            "perf_6m": None,
            "perf_1y": None,
            "ma50": None,
            "ma200": None,
            "rsi14": None,
            "volatility": None,
            "avg_volume": None,
            "history": [],
            "status": "error",
            "error": str(exc),
            "from_cache": False,
        }


def fetch_many_market_data(
    tickers: list[str] | pd.Series,
    period: str = "2y",
    force_refresh: bool = False,
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for ticker in [str(t).upper().strip() for t in tickers if str(t).strip()]:
        results[ticker] = fetch_market_data(ticker, period=period, force_refresh=force_refresh)
    return results


def history_to_frame(history: list[dict[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(history, pd.DataFrame):
        frame = history.copy()
    else:
        frame = pd.DataFrame(history or [])
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"])
    for col in ["close", "ma50", "ma200", "volume"]:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame.sort_values("date")

from database import list_price_alerts, mark_price_alert_triggered, upsert_market_cache


def get_fx_rate(from_currency: str, to_currency: str) -> float:
    from_currency = (from_currency or "EUR").upper()
    to_currency = (to_currency or "EUR").upper()
    if from_currency == to_currency:
        return 1.0
    pair = f"{from_currency}{to_currency}=X"
    data = fetch_market_data(pair, period="6mo")
    return float(data.get("price") or 1.0)


def normalize_to_eur(value: float, currency: str) -> float:
    return float(value) * get_fx_rate(currency, "EUR")


def check_price_alerts(user_id: str, market_data: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    alerts_df = list_price_alerts(active_only=True, user_id=user_id)
    triggered = []
    for _, a in alerts_df.iterrows():
        ticker = a["ticker"]
        data = market_data.get(ticker) or fetch_market_data(ticker)
        price = data.get("price")
        ma200 = data.get("ma200")
        rsi = data.get("rsi14")
        cond = False
        if a["alert_type"] == "price_below" and price is not None and a["threshold"] is not None:
            cond = price <= a["threshold"]
        elif a["alert_type"] == "price_above" and price is not None and a["threshold"] is not None:
            cond = price >= a["threshold"]
        elif a["alert_type"] == "ma200_cross" and price is not None and ma200 is not None:
            cond = price >= ma200
        elif a["alert_type"] == "rsi_oversold" and rsi is not None:
            cond = rsi < 30
        if cond:
            mark_price_alert_triggered(int(a["id"]), user_id=user_id)
            triggered.append({"ticker": ticker, "type": a["alert_type"], "price": price, "threshold": a["threshold"]})
    return triggered


def fetch_dividends(ticker: str) -> pd.DataFrame:
    import yfinance as yf

    series = yf.Ticker(ticker).dividends
    if series is None or len(series) == 0:
        return pd.DataFrame(columns=["date", "amount_per_share"])
    df = series.reset_index()
    df.columns = ["date", "amount_per_share"]
    return df
