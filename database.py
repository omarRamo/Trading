from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from config import DB_PATH, DEFAULT_SETTINGS, DEFAULT_WATCHLIST, DEMO_POSITIONS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS assets (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                asset_type TEXT NOT NULL CHECK(asset_type IN ('ETF', 'ACTION')),
                currency TEXT NOT NULL DEFAULT 'EUR',
                sector TEXT,
                region TEXT,
                category TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                revolut_available INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                asset_name TEXT,
                asset_type TEXT NOT NULL CHECK(asset_type IN ('ETF', 'ACTION')),
                transaction_type TEXT NOT NULL DEFAULT 'BUY',
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                transaction_date TEXT NOT NULL,
                currency TEXT NOT NULL DEFAULT 'EUR',
                fees REAL NOT NULL DEFAULT 0,
                amount REAL NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_positions (
                ticker TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                asset_type TEXT NOT NULL CHECK(asset_type IN ('ETF', 'ACTION')),
                quantity REAL NOT NULL,
                avg_buy_price REAL NOT NULL,
                purchase_date TEXT,
                currency TEXT NOT NULL DEFAULT 'EUR',
                invested_amount REAL NOT NULL,
                fees REAL NOT NULL DEFAULT 0,
                sector TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_data_cache (
                ticker TEXT PRIMARY KEY,
                price REAL,
                previous_close REAL,
                change_1d REAL,
                perf_1m REAL,
                perf_3m REAL,
                perf_6m REAL,
                perf_1y REAL,
                ma50 REAL,
                ma200 REAL,
                rsi14 REAL,
                volatility REAL,
                avg_volume REAL,
                history_json TEXT,
                fetched_at TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                name TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                score REAL NOT NULL,
                recommended_amount REAL NOT NULL,
                prudence_level TEXT NOT NULL,
                reasons TEXT NOT NULL,
                metrics_snapshot TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS monthly_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_date TEXT NOT NULL,
                monthly_amount REAL NOT NULL,
                etf_amount REAL NOT NULL,
                stock_amount REAL NOT NULL,
                cash_amount REAL NOT NULL,
                details_json TEXT NOT NULL,
                warnings_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
    seed_default_settings()
    seed_default_watchlist()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def seed_default_settings() -> None:
    existing = load_settings(include_defaults=False)
    with get_connection() as conn:
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                conn.execute(
                    "INSERT OR REPLACE INTO settings(key, value, updated_at) VALUES (?, ?, ?)",
                    (key, _json_dumps(value), utc_now()),
                )
        conn.commit()


def seed_default_watchlist() -> None:
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        if count:
            return
        now = utc_now()
        for asset in DEFAULT_WATCHLIST:
            conn.execute(
                """
                INSERT OR REPLACE INTO assets(
                    ticker, name, asset_type, currency, sector, region, category,
                    is_active, revolut_available, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?)
                """,
                (
                    asset["ticker"].upper(),
                    asset["name"],
                    asset["asset_type"],
                    asset.get("currency", "EUR"),
                    asset.get("sector", ""),
                    asset.get("region", ""),
                    asset.get("category", ""),
                    asset.get("notes", ""),
                    now,
                    now,
                ),
            )
        conn.commit()


def seed_demo_portfolio(overwrite: bool = False) -> None:
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM portfolio_positions").fetchone()[0]
        if count and not overwrite:
            return
        if overwrite:
            conn.execute("DELETE FROM portfolio_positions")
            conn.execute("DELETE FROM transactions")
        now = utc_now()
        for position in DEMO_POSITIONS:
            conn.execute(
                """
                INSERT OR REPLACE INTO portfolio_positions(
                    ticker, name, asset_type, quantity, avg_buy_price, purchase_date,
                    currency, invested_amount, fees, sector, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position["ticker"].upper(),
                    position["name"],
                    position["asset_type"],
                    position["quantity"],
                    position["avg_buy_price"],
                    position["purchase_date"],
                    position["currency"],
                    position["invested_amount"],
                    position["fees"],
                    position.get("sector", ""),
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO transactions(
                    ticker, asset_name, asset_type, transaction_type, quantity, price,
                    transaction_date, currency, fees, amount, notes, created_at
                )
                VALUES (?, ?, ?, 'BUY', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position["ticker"].upper(),
                    position["name"],
                    position["asset_type"],
                    position["quantity"],
                    position["avg_buy_price"],
                    position["purchase_date"],
                    position["currency"],
                    position["fees"],
                    position["invested_amount"],
                    "Transaction fictive de demonstration",
                    now,
                ),
            )
        conn.commit()


def load_settings(include_defaults: bool = True) -> dict[str, Any]:
    data = dict(DEFAULT_SETTINGS) if include_defaults else {}
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    for row in rows:
        data[row["key"]] = _json_loads(row["value"])
    return data


def save_settings(settings: dict[str, Any]) -> None:
    with get_connection() as conn:
        for key, value in settings.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings(key, value, updated_at) VALUES (?, ?, ?)",
                (key, _json_dumps(value), utc_now()),
            )
        conn.commit()


def get_assets(active_only: bool = True) -> pd.DataFrame:
    sql = "SELECT * FROM assets"
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY asset_type, ticker"
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn)


def upsert_asset(asset: dict[str, Any]) -> None:
    now = utc_now()
    ticker = str(asset["ticker"]).upper().strip()
    with get_connection() as conn:
        existing = conn.execute("SELECT created_at FROM assets WHERE ticker = ?", (ticker,)).fetchone()
        conn.execute(
            """
            INSERT OR REPLACE INTO assets(
                ticker, name, asset_type, currency, sector, region, category,
                is_active, revolut_available, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                asset.get("name", ticker),
                asset.get("asset_type", "ACTION"),
                asset.get("currency", "EUR"),
                asset.get("sector", ""),
                asset.get("region", ""),
                asset.get("category", ""),
                int(asset.get("is_active", 1)),
                int(asset.get("revolut_available", 1)),
                asset.get("notes", ""),
                existing["created_at"] if existing else now,
                now,
            ),
        )
        conn.commit()


def set_asset_active(ticker: str, is_active: bool) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE assets SET is_active = ?, updated_at = ? WHERE ticker = ?",
            (int(is_active), utc_now(), ticker.upper()),
        )
        conn.commit()


def get_positions() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM portfolio_positions ORDER BY asset_type, ticker", conn)


def upsert_position(position: dict[str, Any]) -> None:
    now = utc_now()
    ticker = str(position["ticker"]).upper().strip()
    quantity = float(position.get("quantity", 0))
    avg_buy_price = float(position.get("avg_buy_price", 0))
    invested_amount = float(position.get("invested_amount") or quantity * avg_buy_price)
    fees = float(position.get("fees", 0))
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT created_at FROM portfolio_positions WHERE ticker = ?", (ticker,)
        ).fetchone()
        conn.execute(
            """
            INSERT OR REPLACE INTO portfolio_positions(
                ticker, name, asset_type, quantity, avg_buy_price, purchase_date,
                currency, invested_amount, fees, sector, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                position.get("name", ticker),
                position.get("asset_type", "ACTION"),
                quantity,
                avg_buy_price,
                position.get("purchase_date"),
                position.get("currency", "EUR"),
                invested_amount,
                fees,
                position.get("sector", ""),
                existing["created_at"] if existing else now,
                now,
            ),
        )
        conn.commit()


def delete_position(ticker: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM portfolio_positions WHERE ticker = ?", (ticker.upper(),))
        conn.commit()


def add_transaction(transaction: dict[str, Any], update_position: bool = False) -> None:
    ticker = str(transaction["ticker"]).upper().strip()
    quantity = float(transaction.get("quantity", 0))
    price = float(transaction.get("price", 0))
    fees = float(transaction.get("fees", 0))
    amount = float(transaction.get("amount") or quantity * price + fees)
    tx_type = transaction.get("transaction_type", "BUY")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO transactions(
                ticker, asset_name, asset_type, transaction_type, quantity, price,
                transaction_date, currency, fees, amount, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker,
                transaction.get("asset_name", ticker),
                transaction.get("asset_type", "ACTION"),
                tx_type,
                quantity,
                price,
                transaction.get("transaction_date"),
                transaction.get("currency", "EUR"),
                fees,
                amount,
                transaction.get("notes", ""),
                utc_now(),
            ),
        )
        conn.commit()
    if update_position and tx_type == "BUY":
        _apply_buy_to_position(transaction | {"ticker": ticker, "amount": amount, "fees": fees})


def _apply_buy_to_position(transaction: dict[str, Any]) -> None:
    ticker = str(transaction["ticker"]).upper()
    positions = get_positions()
    current = positions[positions["ticker"] == ticker]
    qty = float(transaction.get("quantity", 0))
    amount = float(transaction.get("amount", 0))
    price = float(transaction.get("price", 0))
    fees = float(transaction.get("fees", 0))
    if current.empty:
        upsert_position(
            {
                "ticker": ticker,
                "name": transaction.get("asset_name", ticker),
                "asset_type": transaction.get("asset_type", "ACTION"),
                "quantity": qty,
                "avg_buy_price": price,
                "purchase_date": transaction.get("transaction_date"),
                "currency": transaction.get("currency", "EUR"),
                "invested_amount": amount,
                "fees": fees,
                "sector": transaction.get("sector", ""),
            }
        )
        return
    row = current.iloc[0]
    new_qty = float(row["quantity"]) + qty
    new_invested = float(row["invested_amount"]) + amount
    new_avg = new_invested / new_qty if new_qty else 0
    upsert_position(
        {
            "ticker": ticker,
            "name": row["name"],
            "asset_type": row["asset_type"],
            "quantity": new_qty,
            "avg_buy_price": new_avg,
            "purchase_date": row["purchase_date"],
            "currency": row["currency"],
            "invested_amount": new_invested,
            "fees": float(row["fees"]) + fees,
            "sector": row.get("sector", ""),
        }
    )


def get_transactions() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM transactions ORDER BY transaction_date DESC, id DESC", conn)


def get_market_cache(ticker: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM market_data_cache WHERE ticker = ?", (ticker.upper(),)).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["history"] = _json_loads(data.pop("history_json") or "[]")
    return data


def upsert_market_cache(ticker: str, metrics: dict[str, Any], history_rows: list[dict[str, Any]]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO market_data_cache(
                ticker, price, previous_close, change_1d, perf_1m, perf_3m, perf_6m,
                perf_1y, ma50, ma200, rsi14, volatility, avg_volume, history_json,
                fetched_at, status, error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker.upper(),
                metrics.get("price"),
                metrics.get("previous_close"),
                metrics.get("change_1d"),
                metrics.get("perf_1m"),
                metrics.get("perf_3m"),
                metrics.get("perf_6m"),
                metrics.get("perf_1y"),
                metrics.get("ma50"),
                metrics.get("ma200"),
                metrics.get("rsi14"),
                metrics.get("volatility"),
                metrics.get("avg_volume"),
                _json_dumps(history_rows),
                utc_now(),
                metrics.get("status", "ok"),
                metrics.get("error"),
            ),
        )
        conn.commit()


def save_recommendations(recommendations: list[dict[str, Any]]) -> None:
    if not recommendations:
        return
    run_date = utc_now()
    with get_connection() as conn:
        for rec in recommendations:
            conn.execute(
                """
                INSERT INTO recommendations(
                    run_date, ticker, name, asset_type, score, recommended_amount,
                    prudence_level, reasons, metrics_snapshot, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_date,
                    rec["ticker"],
                    rec["name"],
                    rec["asset_type"],
                    float(rec["score"]),
                    float(rec.get("recommended_amount", 0)),
                    rec.get("prudence_level", "à surveiller"),
                    _json_dumps(rec.get("reasons", [])),
                    _json_dumps(rec.get("metrics", {})),
                    run_date,
                ),
            )
        conn.commit()


def get_latest_recommendations(limit: int = 50) -> pd.DataFrame:
    with get_connection() as conn:
        latest = conn.execute("SELECT MAX(run_date) FROM recommendations").fetchone()[0]
        if not latest:
            return pd.DataFrame()
        return pd.read_sql_query(
            "SELECT * FROM recommendations WHERE run_date = ? ORDER BY score DESC LIMIT ?",
            conn,
            params=(latest, limit),
        )


def save_monthly_plan(plan: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO monthly_plans(
                plan_date, monthly_amount, etf_amount, stock_amount, cash_amount,
                details_json, warnings_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan.get("plan_date", utc_now()),
                float(plan["monthly_amount"]),
                float(plan["bucket_amounts"]["ETF"]),
                float(plan["bucket_amounts"]["ACTION"]),
                float(plan["bucket_amounts"]["CASH"]),
                _json_dumps(plan.get("items", [])),
                _json_dumps(plan.get("warnings", [])),
                utc_now(),
            ),
        )
        conn.commit()


def get_latest_monthly_plan() -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM monthly_plans ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    data = dict(row)
    data["items"] = _json_loads(data.pop("details_json") or "[]")
    data["warnings"] = _json_loads(data.pop("warnings_json") or "[]")
    return data
