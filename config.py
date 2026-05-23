from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "trading_app.sqlite3"

CACHE_TTL_HOURS = 6
DEFAULT_CURRENCY = "EUR"

DEFAULT_SETTINGS = {
    "capital_total": 12000.0,
    "cash_available": 1200.0,
    "monthly_investment": 1000.0,
    "target_allocation_etf": 0.70,
    "target_allocation_stocks": 0.20,
    "target_allocation_cash": 0.10,
    "base_currency": DEFAULT_CURRENCY,
    "max_individual_position": 0.08,
    "hard_max_individual_position": 0.10,
    "risk_profile": "equilibre",
    "investment_horizon": "long terme",
    "tech_exposure_limit": 0.45,
    "correlation_warning_threshold": 0.85,
    "auto_sync_market_data": True,
    "auto_sync_interval_hours": 6,
    "last_market_sync_at": "",
}

RISK_PROFILES = ["prudent", "equilibre", "dynamique"]

DEFAULT_WATCHLIST = [
    {
        "ticker": "VUSA.L",
        "name": "Vanguard S&P 500 UCITS ETF",
        "asset_type": "ETF",
        "currency": "GBP",
        "sector": "Diversifie",
        "region": "USA",
        "category": "S&P 500",
        "notes": "Exemple Revolut possible, disponibilite a verifier.",
    },
    {
        "ticker": "CSPX.L",
        "name": "iShares Core S&P 500 UCITS ETF",
        "asset_type": "ETF",
        "currency": "USD",
        "sector": "Diversifie",
        "region": "USA",
        "category": "S&P 500",
        "notes": "Alternative S&P 500 selon disponibilite Revolut.",
    },
    {
        "ticker": "EQQQ.L",
        "name": "Invesco EQQQ Nasdaq-100 UCITS ETF",
        "asset_type": "ETF",
        "currency": "GBP",
        "sector": "Technologie",
        "region": "USA",
        "category": "Nasdaq 100",
        "notes": "ETF plus concentre en technologie.",
    },
    {
        "ticker": "IWDA.AS",
        "name": "iShares Core MSCI World UCITS ETF",
        "asset_type": "ETF",
        "currency": "EUR",
        "sector": "Diversifie",
        "region": "Monde",
        "category": "MSCI World",
        "notes": "ETF coeur monde developpe.",
    },
    {"ticker": "NVDA", "name": "NVIDIA", "asset_type": "ACTION", "currency": "USD", "sector": "Technologie", "region": "USA", "category": "Semi-conducteurs", "notes": ""},
    {"ticker": "MSFT", "name": "Microsoft", "asset_type": "ACTION", "currency": "USD", "sector": "Technologie", "region": "USA", "category": "Logiciels", "notes": ""},
    {"ticker": "AAPL", "name": "Apple", "asset_type": "ACTION", "currency": "USD", "sector": "Technologie", "region": "USA", "category": "Materiel", "notes": ""},
    {"ticker": "GOOGL", "name": "Alphabet", "asset_type": "ACTION", "currency": "USD", "sector": "Communication", "region": "USA", "category": "Internet", "notes": ""},
    {"ticker": "AMZN", "name": "Amazon", "asset_type": "ACTION", "currency": "USD", "sector": "Consommation cyclique", "region": "USA", "category": "E-commerce", "notes": ""},
    {"ticker": "TSLA", "name": "Tesla", "asset_type": "ACTION", "currency": "USD", "sector": "Consommation cyclique", "region": "USA", "category": "Automobile", "notes": ""},
    {"ticker": "ASML", "name": "ASML Holding", "asset_type": "ACTION", "currency": "EUR", "sector": "Technologie", "region": "Europe", "category": "Semi-conducteurs", "notes": ""},
    {"ticker": "LVMH.PA", "name": "LVMH", "asset_type": "ACTION", "currency": "EUR", "sector": "Consommation cyclique", "region": "Europe", "category": "Luxe", "notes": ""},
    {"ticker": "MC.PA", "name": "LVMH alias Euronext", "asset_type": "ACTION", "currency": "EUR", "sector": "Consommation cyclique", "region": "Europe", "category": "Luxe", "notes": "Ticker alternatif a verifier dans Revolut."},
    {"ticker": "AIR.PA", "name": "Airbus", "asset_type": "ACTION", "currency": "EUR", "sector": "Industrie", "region": "Europe", "category": "Aerospace", "notes": ""},
]

DEMO_POSITIONS = [
    {
        "ticker": "IWDA.AS",
        "name": "iShares Core MSCI World UCITS ETF",
        "asset_type": "ETF",
        "quantity": 28.0,
        "avg_buy_price": 85.0,
        "purchase_date": "2025-10-15",
        "currency": "EUR",
        "invested_amount": 2380.0,
        "fees": 2.0,
        "sector": "Diversifie",
    },
    {
        "ticker": "VUSA.L",
        "name": "Vanguard S&P 500 UCITS ETF",
        "asset_type": "ETF",
        "quantity": 35.0,
        "avg_buy_price": 78.0,
        "purchase_date": "2025-11-12",
        "currency": "GBP",
        "invested_amount": 2730.0,
        "fees": 2.5,
        "sector": "Diversifie",
    },
    {
        "ticker": "MSFT",
        "name": "Microsoft",
        "asset_type": "ACTION",
        "quantity": 4.0,
        "avg_buy_price": 410.0,
        "purchase_date": "2026-01-10",
        "currency": "USD",
        "invested_amount": 1640.0,
        "fees": 1.0,
        "sector": "Technologie",
    },
    {
        "ticker": "ASML",
        "name": "ASML Holding",
        "asset_type": "ACTION",
        "quantity": 1.0,
        "avg_buy_price": 720.0,
        "purchase_date": "2026-02-07",
        "currency": "EUR",
        "invested_amount": 720.0,
        "fees": 1.0,
        "sector": "Technologie",
    },
]

MANUAL_DECISION_PHRASE = "Décision finale à valider manuellement par l’investisseur."

DISCLAIMER = (
    "Compagnon local d'aide a la decision pour une construction patrimoniale long terme. "
    "Les idees affichees sont des signaux pedagogiques incertains, jamais des ordres "
    "d'achat ou de vente. Aucun ordre n'est transmis a Revolut, aucun levier, aucune "
    "marge et aucune vente a decouvert ne sont utilises. "
    f"{MANUAL_DECISION_PHRASE}"
)
