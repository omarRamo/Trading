namespace TradePerso.Domain.MarketData;

public sealed record MarketQuote(
    string Ticker,
    decimal? Price,
    decimal? Change1d,
    decimal? Perf1m,
    decimal? Perf3m,
    decimal? Perf6m,
    decimal? Perf1y,
    decimal? Ma50,
    decimal? Ma200,
    decimal? Rsi14,
    decimal? Volatility,
    decimal? AvgVolume,
    string Currency,
    string Status,
    string? Error,
    DateTimeOffset FetchedAt,
    IReadOnlyList<HistoryPoint> History);

public sealed record HistoryPoint(DateOnly Date, decimal Close);
