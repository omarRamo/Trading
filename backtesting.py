from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    curve: pd.DataFrame
    metrics: pd.DataFrame
    warnings: list[str]


def _normalise_download(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw.empty:
        return raw
    if isinstance(raw.columns, pd.MultiIndex):
        if "Adj Close" in raw.columns.get_level_values(0):
            prices = raw["Adj Close"].copy()
        elif "Close" in raw.columns.get_level_values(0):
            prices = raw["Close"].copy()
        else:
            prices = raw.xs(raw.columns.get_level_values(0)[0], axis=1, level=0)
    else:
        col = "Adj Close" if "Adj Close" in raw.columns else "Close"
        prices = raw[[col]].rename(columns={col: tickers[0]})
    if isinstance(prices, pd.Series):
        prices = prices.to_frame(tickers[0])
    prices = prices[[col for col in prices.columns if col in tickers]]
    return prices.dropna(how="all")


def download_monthly_prices(tickers: list[str], start: str, end: str) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    clean_tickers = [ticker.upper().strip() for ticker in tickers if ticker.strip()]
    if not clean_tickers:
        return pd.DataFrame(), ["Aucun ticker selectionne."]
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame(), ["Le package yfinance n'est pas installe."]
    raw = yf.download(clean_tickers, start=start, end=end, progress=False, auto_adjust=False, threads=False)
    prices = _normalise_download(raw, clean_tickers)
    if prices.empty:
        return prices, ["Aucune donnee historique disponible pour cette selection."]
    missing = sorted(set(clean_tickers) - set(prices.columns))
    if missing:
        warnings.append("Tickers ignores faute de donnees: " + ", ".join(missing))
    prices = prices.resample("ME").last().dropna(how="all")
    return prices, warnings


def _buy_equal_weight(units: dict[str, float], prices: pd.Series, amount: float, tickers: list[str]) -> float:
    available = [ticker for ticker in tickers if ticker in prices.index and pd.notna(prices[ticker]) and prices[ticker] > 0]
    if not available or amount <= 0:
        return amount
    per_asset = amount / len(available)
    unused = 0.0
    for ticker in available:
        units[ticker] = units.get(ticker, 0.0) + per_asset / float(prices[ticker])
    return unused


def _portfolio_value(units: dict[str, float], prices: pd.Series, cash: float = 0.0) -> float:
    value = cash
    for ticker, qty in units.items():
        if ticker in prices.index and pd.notna(prices[ticker]):
            value += qty * float(prices[ticker])
    return float(value)


def calculate_metrics(series: pd.Series) -> dict[str, float]:
    clean = series.dropna()
    if len(clean) < 2:
        return {"performance": 0.0, "cagr": 0.0, "volatility": 0.0, "max_drawdown": 0.0}
    total_return = clean.iloc[-1] / clean.iloc[0] - 1 if clean.iloc[0] else 0.0
    years = max((clean.index[-1] - clean.index[0]).days / 365.25, 1 / 12)
    cagr = (clean.iloc[-1] / clean.iloc[0]) ** (1 / years) - 1 if clean.iloc[0] > 0 else 0.0
    returns = clean.pct_change().dropna()
    volatility = returns.std() * np.sqrt(12) if not returns.empty else 0.0
    peak = clean.cummax()
    drawdown = clean / peak - 1
    return {
        "performance": float(total_return),
        "cagr": float(cagr),
        "volatility": float(volatility),
        "max_drawdown": float(drawdown.min()),
    }


def run_backtest(
    etf_tickers: list[str],
    stock_tickers: list[str],
    monthly_amount: float,
    start: str,
    end: str,
) -> BacktestResult:
    all_tickers = list(dict.fromkeys([*etf_tickers, *stock_tickers]))
    prices, warnings = download_monthly_prices(all_tickers, start, end)
    if prices.empty:
        return BacktestResult(pd.DataFrame(), pd.DataFrame(), warnings)

    etfs = [ticker for ticker in etf_tickers if ticker in prices.columns]
    stocks = [ticker for ticker in stock_tickers if ticker in prices.columns]
    if not etfs:
        return BacktestResult(pd.DataFrame(), pd.DataFrame(), warnings + ["Le backtest exige au moins un ETF avec donnees."])

    dca_units: dict[str, float] = {}
    mixed_units: dict[str, float] = {}
    mixed_cash = 0.0
    lump_units: dict[str, float] = {}
    lump_cash = 0.0
    rows = []
    total_months = len(prices)
    lump_amount = monthly_amount * total_months

    first_prices = prices.iloc[0]
    lump_cash += _buy_equal_weight(lump_units, first_prices, lump_amount, etfs)

    for idx, row in prices.iterrows():
        _buy_equal_weight(dca_units, row, monthly_amount, etfs)
        etf_budget = monthly_amount * 0.70
        stock_budget = monthly_amount * 0.20
        cash_budget = monthly_amount * 0.10
        mixed_cash += cash_budget
        _buy_equal_weight(mixed_units, row, etf_budget, etfs)
        if stocks:
            _buy_equal_weight(mixed_units, row, stock_budget, stocks)
        else:
            mixed_cash += stock_budget
        rows.append(
            {
                "date": idx,
                "DCA ETF": _portfolio_value(dca_units, row),
                "70/20/10": _portfolio_value(mixed_units, row, mixed_cash),
                "Achat unique depart": _portfolio_value(lump_units, row, lump_cash),
                "Capital verse DCA": monthly_amount * (len(rows) + 1),
                "Capital achat unique": lump_amount,
            }
        )

    curve = pd.DataFrame(rows).set_index("date")
    metrics_rows = []
    for name in ["DCA ETF", "70/20/10", "Achat unique depart"]:
        values = calculate_metrics(curve[name])
        metrics_rows.append({"strategie": name, **values})
    metrics = pd.DataFrame(metrics_rows)
    return BacktestResult(curve=curve, metrics=metrics, warnings=warnings)
