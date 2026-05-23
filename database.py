from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from config import DB_PATH, DEFAULT_SETTINGS, DEFAULT_WATCHLIST, DEMO_POSITIONS

DEFAULT_PROFILE_ID = "local_legacy"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_current_user_id() -> str:
    try:
        if "streamlit" not in sys.modules:
            return DEFAULT_PROFILE_ID
        import streamlit as st

        return st.session_state.get("user_id") or DEFAULT_PROFILE_ID
    except Exception:
        return DEFAULT_PROFILE_ID


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _primary_key_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    keyed = [(row["pk"], row["name"]) for row in rows if row["pk"]]
    return [name for _, name in sorted(keyed)]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def initialize_database() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                provider_subject TEXT,
                email TEXT NOT NULL,
                name TEXT,
                picture_url TEXT,
                created_at TEXT NOT NULL,
                last_login_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                user_id TEXT NOT NULL DEFAULT 'local_legacy',
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, key)
            );

            CREATE TABLE IF NOT EXISTS assets (
                user_id TEXT NOT NULL DEFAULT 'local_legacy',
                ticker TEXT NOT NULL,
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
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, ticker)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'local_legacy',
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
                user_id TEXT NOT NULL DEFAULT 'local_legacy',
                ticker TEXT NOT NULL,
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
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, ticker)
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
                user_id TEXT NOT NULL DEFAULT 'local_legacy',
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
                user_id TEXT NOT NULL DEFAULT 'local_legacy',
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
    migrate_user_scoped_tables()
    ensure_local_user()
    seed_default_settings()
    seed_default_watchlist()


def migrate_user_scoped_tables() -> None:
    with get_connection() as conn:
        if _table_exists(conn, "settings"):
            columns = _table_columns(conn, "settings")
            if "user_id" not in columns or _primary_key_columns(conn, "settings") != ["user_id", "key"]:
                conn.execute("ALTER TABLE settings RENAME TO settings_legacy")
                conn.execute(
                    """
                    CREATE TABLE settings (
                        user_id TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, key)
                    )
                    """
                )
                legacy_columns = _table_columns(conn, "settings_legacy")
                if {"key", "value", "updated_at"}.issubset(set(legacy_columns)):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO settings(user_id, key, value, updated_at)
                        SELECT ?, key, value, updated_at FROM settings_legacy
                        """,
                        (DEFAULT_PROFILE_ID,),
                    )
                conn.execute("DROP TABLE settings_legacy")

        if _table_exists(conn, "assets"):
            columns = _table_columns(conn, "assets")
            if "user_id" not in columns or _primary_key_columns(conn, "assets") != ["user_id", "ticker"]:
                conn.execute("ALTER TABLE assets RENAME TO assets_legacy")
                conn.execute(
                    """
                    CREATE TABLE assets (
                        user_id TEXT NOT NULL,
                        ticker TEXT NOT NULL,
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
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, ticker)
                    )
                    """
                )
                legacy_columns = _table_columns(conn, "assets_legacy")
                if {"ticker", "name", "asset_type", "currency", "created_at", "updated_at"}.issubset(set(legacy_columns)):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO assets(
                            user_id, ticker, name, asset_type, currency, sector, region,
                            category, is_active, revolut_available, notes, created_at, updated_at
                        )
                        SELECT ?, ticker, name, asset_type, currency, sector, region,
                               category, is_active, revolut_available, notes, created_at, updated_at
                        FROM assets_legacy
                        """,
                        (DEFAULT_PROFILE_ID,),
                    )
                conn.execute("DROP TABLE assets_legacy")

        if _table_exists(conn, "portfolio_positions"):
            columns = _table_columns(conn, "portfolio_positions")
            if "user_id" not in columns or _primary_key_columns(conn, "portfolio_positions") != ["user_id", "ticker"]:
                conn.execute("ALTER TABLE portfolio_positions RENAME TO portfolio_positions_legacy")
                conn.execute(
                    """
                    CREATE TABLE portfolio_positions (
                        user_id TEXT NOT NULL,
                        ticker TEXT NOT NULL,
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
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, ticker)
                    )
                    """
                )
                legacy_columns = _table_columns(conn, "portfolio_positions_legacy")
                if {"ticker", "name", "asset_type", "quantity", "avg_buy_price", "currency", "invested_amount", "created_at", "updated_at"}.issubset(set(legacy_columns)):
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO portfolio_positions(
                            user_id, ticker, name, asset_type, quantity, avg_buy_price,
                            purchase_date, currency, invested_amount, fees, sector,
                            created_at, updated_at
                        )
                        SELECT ?, ticker, name, asset_type, quantity, avg_buy_price,
                               purchase_date, currency, invested_amount, fees, sector,
                               created_at, updated_at
                        FROM portfolio_positions_legacy
                        """,
                        (DEFAULT_PROFILE_ID,),
                    )
                conn.execute("DROP TABLE portfolio_positions_legacy")

        for table in ["transactions", "recommendations", "monthly_plans"]:
            if _table_exists(conn, table) and "user_id" not in _table_columns(conn, table):
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id TEXT NOT NULL DEFAULT '{DEFAULT_PROFILE_ID}'")
        conn.commit()


def ensure_local_user() -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users(id, provider, provider_subject, email, name, picture_url, created_at, last_login_at)
            VALUES (?, 'local', ?, 'local@trading.app', 'Profil local', '', ?, ?)
            """,
            (DEFAULT_PROFILE_ID, DEFAULT_PROFILE_ID, now, now),
        )
        conn.commit()


def upsert_google_user(profile: dict[str, Any]) -> dict[str, Any]:
    subject = str(profile["sub"])
    user_id = f"google:{subject}"
    now = utc_now()
    with get_connection() as conn:
        existing = conn.execute("SELECT created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.execute(
            """
            INSERT OR REPLACE INTO users(
                id, provider, provider_subject, email, name, picture_url, created_at, last_login_at
            )
            VALUES (?, 'google', ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                subject,
                profile.get("email", ""),
                profile.get("name", profile.get("email", "Compte Google")),
                profile.get("picture", ""),
                existing["created_at"] if existing else now,
                now,
            ),
        )
        conn.commit()
    initialize_user_defaults(user_id)
    return get_user(user_id) or {"id": user_id, **profile}


def get_user(user_id: str | None = None) -> dict[str, Any] | None:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def initialize_user_defaults(user_id: str) -> None:
    seed_default_settings(user_id=user_id)
    seed_default_watchlist(user_id=user_id)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def seed_default_settings(user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    existing = load_settings(include_defaults=False, user_id=user_id)
    with get_connection() as conn:
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                conn.execute(
                    "INSERT OR REPLACE INTO settings(user_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                    (user_id, key, _json_dumps(value), utc_now()),
                )
        conn.commit()


def seed_default_watchlist(user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM assets WHERE user_id = ?", (user_id,)).fetchone()[0]
        if count:
            return
        now = utc_now()
        for asset in DEFAULT_WATCHLIST:
            conn.execute(
                """
                INSERT OR REPLACE INTO assets(
                    user_id, ticker, name, asset_type, currency, sector, region, category,
                    is_active, revolut_available, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?, ?)
                """,
                (
                    user_id,
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


def seed_demo_portfolio(overwrite: bool = False, user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM portfolio_positions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        if count and not overwrite:
            return
        if overwrite:
            conn.execute("DELETE FROM portfolio_positions WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        now = utc_now()
        for position in DEMO_POSITIONS:
            conn.execute(
                """
                INSERT OR REPLACE INTO portfolio_positions(
                    user_id, ticker, name, asset_type, quantity, avg_buy_price, purchase_date,
                    currency, invested_amount, fees, sector, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
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
                    user_id, ticker, asset_name, asset_type, transaction_type, quantity, price,
                    transaction_date, currency, fees, amount, notes, created_at
                )
                VALUES (?, ?, ?, ?, 'BUY', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
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


def load_settings(include_defaults: bool = True, user_id: str | None = None) -> dict[str, Any]:
    user_id = user_id or get_current_user_id()
    data = dict(DEFAULT_SETTINGS) if include_defaults else {}
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings WHERE user_id = ?", (user_id,)).fetchall()
    for row in rows:
        data[row["key"]] = _json_loads(row["value"])
    return data


def save_settings(settings: dict[str, Any], user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        for key, value in settings.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings(user_id, key, value, updated_at) VALUES (?, ?, ?, ?)",
                (user_id, key, _json_dumps(value), utc_now()),
            )
        conn.commit()


def get_assets(active_only: bool = True, user_id: str | None = None) -> pd.DataFrame:
    user_id = user_id or get_current_user_id()
    sql = "SELECT * FROM assets WHERE user_id = ?"
    params: list[Any] = [user_id]
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY asset_type, ticker"
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def upsert_asset(asset: dict[str, Any], user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    now = utc_now()
    ticker = str(asset["ticker"]).upper().strip()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT created_at FROM assets WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        conn.execute(
            """
            INSERT OR REPLACE INTO assets(
                user_id, ticker, name, asset_type, currency, sector, region, category,
                is_active, revolut_available, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
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


def set_asset_active(ticker: str, is_active: bool, user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        conn.execute(
            "UPDATE assets SET is_active = ?, updated_at = ? WHERE user_id = ? AND ticker = ?",
            (int(is_active), utc_now(), user_id, ticker.upper()),
        )
        conn.commit()


def get_positions(user_id: str | None = None) -> pd.DataFrame:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM portfolio_positions WHERE user_id = ? ORDER BY asset_type, ticker",
            conn,
            params=(user_id,),
        )


def upsert_position(position: dict[str, Any], user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    now = utc_now()
    ticker = str(position["ticker"]).upper().strip()
    quantity = float(position.get("quantity", 0))
    avg_buy_price = float(position.get("avg_buy_price", 0))
    invested_amount = float(position.get("invested_amount") or quantity * avg_buy_price)
    fees = float(position.get("fees", 0))
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT created_at FROM portfolio_positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        conn.execute(
            """
            INSERT OR REPLACE INTO portfolio_positions(
                user_id, ticker, name, asset_type, quantity, avg_buy_price, purchase_date,
                currency, invested_amount, fees, sector, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
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


def delete_position(ticker: str, user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM portfolio_positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker.upper()),
        )
        conn.commit()


def add_transaction(transaction: dict[str, Any], update_position: bool = False, user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
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
                user_id, ticker, asset_name, asset_type, transaction_type, quantity, price,
                transaction_date, currency, fees, amount, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
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
        _apply_buy_to_position(transaction | {"ticker": ticker, "amount": amount, "fees": fees}, user_id=user_id)


def _apply_buy_to_position(transaction: dict[str, Any], user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    ticker = str(transaction["ticker"]).upper()
    positions = get_positions(user_id=user_id)
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
            },
            user_id=user_id,
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
        },
        user_id=user_id,
    )


def get_transactions(user_id: str | None = None) -> pd.DataFrame:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY transaction_date DESC, id DESC",
            conn,
            params=(user_id,),
        )


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


# User-scoped overrides kept at the end so older local databases continue to load
# while the application progressively moved from a single profile to Google profiles.
def save_recommendations(recommendations: list[dict[str, Any]], user_id: str | None = None) -> None:
    if not recommendations:
        return
    user_id = user_id or get_current_user_id()
    run_date = utc_now()
    with get_connection() as conn:
        for rec in recommendations:
            conn.execute(
                """
                INSERT INTO recommendations(
                    user_id, run_date, ticker, name, asset_type, score, recommended_amount,
                    prudence_level, reasons, metrics_snapshot, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
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


def get_latest_recommendations(limit: int = 50, user_id: str | None = None) -> pd.DataFrame:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        latest = conn.execute(
            "SELECT MAX(run_date) FROM recommendations WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        if not latest:
            return pd.DataFrame()
        return pd.read_sql_query(
            "SELECT * FROM recommendations WHERE user_id = ? AND run_date = ? ORDER BY score DESC LIMIT ?",
            conn,
            params=(user_id, latest, limit),
        )


def save_monthly_plan(plan: dict[str, Any], user_id: str | None = None) -> None:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO monthly_plans(
                user_id, plan_date, monthly_amount, etf_amount, stock_amount, cash_amount,
                details_json, warnings_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
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


def get_latest_monthly_plan(user_id: str | None = None) -> dict[str, Any] | None:
    user_id = user_id or get_current_user_id()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM monthly_plans WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["items"] = _json_loads(data.pop("details_json") or "[]")
    data["warnings"] = _json_loads(data.pop("warnings_json") or "[]")
    return data


def list_users() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT id, provider, email, name, created_at, last_login_at FROM users ORDER BY last_login_at DESC",
            conn,
        )
