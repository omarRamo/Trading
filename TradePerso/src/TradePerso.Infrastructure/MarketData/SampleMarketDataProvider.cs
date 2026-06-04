using TradePerso.Domain.Contracts;
using TradePerso.Domain.MarketData;

namespace TradePerso.Infrastructure.MarketData;

/// <summary>
/// Deterministic offline provider used for tests, demos and when external APIs are unreachable.
/// Generates a plausible synthetic history derived from the ticker's hash.
/// </summary>
public sealed class SampleMarketDataProvider : IMarketDataProvider
{
    public string ProviderName => "Sample (offline)";

    public Task<MarketQuote> GetQuoteAsync(string ticker, CancellationToken cancellationToken = default)
        => Task.FromResult(Build(ticker));

    public Task<IReadOnlyDictionary<string, MarketQuote>> GetQuotesAsync(
        IEnumerable<string> tickers, CancellationToken cancellationToken = default)
    {
        var dict = tickers.Distinct(StringComparer.OrdinalIgnoreCase)
            .ToDictionary(t => t, Build, StringComparer.OrdinalIgnoreCase);
        return Task.FromResult<IReadOnlyDictionary<string, MarketQuote>>(dict);
    }

    private static MarketQuote Build(string ticker)
    {
        var seed = ticker.Aggregate(17, (a, c) => a * 31 + c);
        var rng = new Random(seed);
        var basePrice = 50m + (decimal)(rng.NextDouble() * 250.0);
        var history = new List<HistoryPoint>(500);
        var price = basePrice;
        var today = DateOnly.FromDateTime(DateTime.UtcNow.Date);
        for (int i = 500; i >= 0; i--)
        {
            var date = today.AddDays(-i);
            if (date.DayOfWeek is DayOfWeek.Saturday or DayOfWeek.Sunday) continue;
            var drift = (decimal)((rng.NextDouble() - 0.49) * 0.02);
            price = Math.Max(1m, price * (1m + drift));
            history.Add(new HistoryPoint(date, Math.Round(price, 4)));
        }

        decimal Last = history[^1].Close;
        decimal? Perf(int days) => history.Count > days
            ? (Last - history[^(days + 1)].Close) / history[^(days + 1)].Close
            : null;

        return new MarketQuote(
            ticker, Last,
            history.Count >= 2 ? (Last - history[^2].Close) / history[^2].Close : null,
            Perf(21), Perf(63), Perf(126), Perf(252),
            history.TakeLast(50).Average(h => h.Close),
            history.Count >= 200 ? history.TakeLast(200).Average(h => h.Close) : null,
            50m + (decimal)(rng.NextDouble() * 40.0 - 20.0),
            0.18m + (decimal)(rng.NextDouble() * 0.10),
            1_000_000m,
            "USD", "ok", null, DateTimeOffset.UtcNow, history);
    }
}
