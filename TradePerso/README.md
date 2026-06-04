## TradePerso — Blazor Web App

Re-implementation of the Streamlit Trading app as a .NET 8 **Blazor Web App** with **Clean Architecture**, a swappable market-data provider, mobile-friendly **MudBlazor** UI, and ASP.NET Core Identity authentication backed by SQLite.

### Solution layout

```
TradePerso/
  TradePerso.sln
  src/
    TradePerso.Domain/         # Entities, enums, contracts (IMarketDataProvider, MarketQuote)
    TradePerso.Application/    # Use-case services, DTOs, repository interfaces, DI registrations
    TradePerso.Infrastructure/ # EF Core SQLite, repositories, market-data providers
    TradePerso.Web/            # Blazor Web App (interactive Server), MudBlazor, Identity
```

Dependency direction (Clean Architecture):

```
Web ──► Application ──► Domain
 │            ▲
 └──► Infrastructure ─┘
```

### Prerequisites

- .NET 8 SDK
- Windows / macOS / Linux

### Run

```powershell
cd TradePerso
dotnet restore
dotnet run --project src/TradePerso.Web
```

Open `https://localhost:5001`. A demo account is seeded on first run:

- email: `omar@tradeperso.local`
- password: `admin`

You can register a new account from the login page.

### Switching the market-data provider

The provider is selected via configuration (`MarketData:Provider` in `appsettings.json`):

```json
"MarketData": {
  "Provider": "Yahoo"   // or "Sample" for offline / deterministic demo data
}
```

To add a new provider:

1. Implement `IMarketDataProvider` (in `TradePerso.Domain.Contracts`) inside `TradePerso.Infrastructure/MarketData/`.
2. Register it in `TradePerso.Infrastructure/DependencyInjection.cs` (switch on `Provider`).
3. Configure it in `appsettings.json`.

The whole application depends only on `IMarketDataProvider`, so no other code needs to change.

### Features (parity with the Streamlit app)

- Multi-user, per-user isolated portfolio, transactions, journal, settings.
- Dashboard with KPIs, allocation vs target, top picks, risk alerts.
- Portfolio with position editor and sector exposure.
- Markets table (price, 1D/1M/3M/1Y, RSI, SMA50/200).
- Monthly plan (70/20/10 budget split with auto picks).
- Investment ideas (scoring + prudence levels: Interesting / Watch / Wait / Avoid).
- Backtest (DCA, 70/20/10 mix, lump sum) with CAGR & max drawdown.
- Transactions journal.
- Trade journal + position sizing calculator.
- Settings (capital, allocation, risk profile, sync).
- Wiki (methodology reference).
- Responsive layout — drawer collapses on mobile, tables degrade gracefully.
- Dark / light theme toggle.

### Persistence

SQLite database is auto-created at first run (`tradeperso.db` next to the `Web` project). Override the connection in `appsettings.json` → `ConnectionStrings:TradePerso`.

### Disclaimer

For personal research only. Not investment advice.
