# Local Monthly Investment Assistant (Revolut Trading)

Local Python application designed as a personal decision-support companion for a prudent, long-term DCA strategy.

Goals:

- provide a clear portfolio view;
- structure market analysis;
- display risk alerts;
- suggest assets worth monitoring;
- prepare an indicative monthly allocation;
- use simple signals: interesting, watch, wait, avoid.

The app never presents outputs as mandatory trading orders. Final buy/sell decisions are always manual and remain fully under the investor's control.

## Authentication

The app supports two modes:

- local account with email, personal details, and password;
- Google OAuth sign-in when configured.

Local account creation is available on the login page. Passwords are stored as salted PBKDF2 hashes, never in plaintext.

The first login or account creation automatically creates a profile. Later logins reopen the same profile.

Each profile has isolated data:

- settings;
- watchlist;
- portfolio;
- transactions;
- investment ideas;
- monthly plans.

Before authentication, the Streamlit sidebar is hidden to avoid exposing internal app pages.

## Strict Rules

- No automated order execution.
- No Revolut order placement integration.
- No leverage.
- No margin trading.
- No short selling.
- No certainty presented as a reliable prediction.
- No proposed buy on a stock already above its concentration limit.

## Target Strategy

- 70% long-term ETFs
- 20% individual stocks
- 10% cash/opportunities
- max risk per individual stock configurable between 5% and 10%

## Structure

```text
Trading/
|-- app.py
|-- streamlit_app.py
|-- config.py
|-- database.py
|-- market_data.py
|-- portfolio.py
|-- strategy.py
|-- risk_management.py
|-- backtesting.py
|-- charts.py
|-- requirements.txt
|-- README.md
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|-- .devcontainer/
|   `-- devcontainer.json
|-- .streamlit/
|   `-- secrets.toml.example
|-- data/
|   `-- trading_app.sqlite3
|-- pages/
|   |-- 1_Portefeuille.py
|   |-- 2_Marches.py
|   |-- 3_Plan_mensuel.py
|   |-- 4_Idees_investissement.py
|   |-- 5_Backtest.py
|   |-- 6_Parametres.py
|   |-- 7_Transactions.py
|   |-- 8_Profil.py
|   `-- 9_Wiki.py
`-- utils/
    |-- __init__.py
    |-- formatting.py
    `-- ui.py
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows, if `python` opens the Microsoft Store shortcut, use:

```bash
py -3 -m pip install -r requirements.txt
```

## Optional Google OAuth Setup

This step is optional if you only want to use local email/password accounts.

Copy the sample file:

```bash
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Then fill in:

```toml
[google_oauth]
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
redirect_uri = "http://localhost:8501"
```

In Google Cloud Console:

- create a project;
- configure the OAuth consent screen;
- create an OAuth client of type `Web application`;
- add `http://localhost:8501` to authorized redirect URIs.

The app only requests `openid email profile` scopes. It does not request Gmail mailbox access.

## Run

```bash
streamlit run app.py
```

Or with the Windows Python launcher:

```bash
py -3 -m streamlit run app.py
```

The app is available locally, usually at:

```text
http://localhost:8501
```

## Streamlit Community Cloud Deployment

The Streamlit Cloud entrypoint is:

```text
streamlit_app.py
```

In Streamlit Community Cloud:

- Repository: `omarRamo/Trading`
- Branch: `main`
- Main file path: `streamlit_app.py`

`streamlit_app.py` imports `app.py`, so local runs and cloud deployment use the same code path.

## Develop From a Phone

The repository includes GitHub Codespaces configuration:

- `.devcontainer/devcontainer.json`
- Streamlit port `8501` auto-forwarded
- dependencies installed from `requirements.txt`

From a phone:

1. Open the GitHub repository.
2. Launch a Codespace from `Code > Codespaces`.
3. In the Codespace terminal, run:

```bash
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

4. Open the forwarded `8501` port URL in your browser.

## GitHub Actions

The workflow `.github/workflows/ci.yml` runs on each push, pull request, or manual trigger.

It validates:

- dependency installation;
- Python bytecode compilation;
- SQLite initialization;
- required baseline local account data for app startup checks;
- default watchlist and sample portfolio data availability.

GitHub Actions is used here for validation. Interactive development from a phone is better handled with GitHub Codespaces.

## Data and Privacy

- Portfolio data, transactions, settings, market cache, computed ideas, and monthly plans are stored in SQLite: `data/trading_app.sqlite3`.
- The app does not send personal data to Revolut.
- External calls are limited to market prices via `yfinance`.
- Google sign-in is only used to identify the local user profile.
- Local accounts use salted PBKDF2 password hashes.
- If a ticker request fails, the app shows a non-blocking error and continues with other assets.
- No order execution API is present.

## SQLite Tables

Tables created automatically on first startup:

- `settings`
- `assets`
- `transactions`
- `portfolio_positions`
- `market_data_cache`
- `recommendations`
- `monthly_plans`
- `users`

The `recommendations` table keeps its technical name to avoid unnecessary migration, while the UI labels this section as investment ideas/candidates.

## Default Watchlist

Tickers are configurable on the Settings page. The initial list includes:

- ETFs: `VUSA.L`, `CSPX.L`, `EQQQ.L`, `IWDA.AS`
- Stocks: `NVDA`, `MSFT`, `AAPL`, `GOOGL`, `AMZN`, `TSLA`, `ASML`, `LVMH.PA`, `MC.PA`, `AIR.PA`

Revolut availability may vary. Always confirm the ticker in Revolut before making any decision.

## Sample Portfolio

From the Dashboard or Settings page, click `Load Sample Portfolio`.

Included example:

- `IWDA.AS`, MSCI World ETF
- `VUSA.L`, S&P 500 ETF
- `MSFT`, individual stock
- `ASML`, individual stock
- available cash: EUR 1,200 by default

## Monthly Strategy Example with EUR 1,000

If current allocation is close to target, the engine starts with:

- about EUR 700 to ETFs;
- about EUR 200 to individual stocks;
- about EUR 100 in cash/opportunities.

Then it adjusts:

- ETF allocation increased when ETF bucket is underweight;
- stock allocation reduced or blocked when stock bucket is overweight;
- cash allocation increased when cash bucket is below target;
- stock line blocked when it exceeds configured per-stock risk limit.

Each idea displays:

- ticker;
- asset type;
- quality score;
- educational signal;
- risk level;
- theoretical max amount under strategy rules;
- rationale;
- caution points;
- manual validation reminder.

## Pages

- Dashboard: summary, allocation, alerts, top candidates, monthly envelope.
- Portfolio: manual position entry, valuation, weights, unrealized P/L, allocation.
- Markets: yfinance indicators, MA50, MA200, RSI, volatility, comparisons.
- Monthly Plan: indicative envelope split and candidates to review.
- Investment Ideas: 0-100 scoring, risk, caution flags, manual validation.
- Backtest: ETF DCA, 70/20/10, one-time initial buy.
- Settings: target allocation, risk, cash, configurable watchlist.
- Transactions: local journal of manually entered operations.
- Profile: user account, local stats, and personal amounts.
- Wiki: simple explanation of pages and key concepts.

## Possible Improvements

- Reliable EUR/USD/GBP FX conversion to value all lines in EUR.
- Revolut CSV import to reduce manual entry.
- Basic fundamental analysis: growth, margins, debt, valuation.
- Finer sector limits per ETF with look-through decomposition.
- More robust scoring by market regime.
- PDF/CSV export for the monthly plan.
- Full unit test coverage and CI hardening.
