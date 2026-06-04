using System.Globalization;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using TradePerso.Domain.Contracts;
using TradePerso.Domain.MarketData;

namespace TradePerso.Infrastructure.MarketData;

/// <summary>
/// Yahoo Finance v8 chart endpoint (no API key required). Best-effort.
/// </summary>
public sealed class YahooFinanceMarketDataProvider : IMarketDataProvider
{
    private readonly HttpClient _http;
    private readonly ILogger<YahooFinanceMarketDataProvider> _log;
    private readonly MarketDataOptions _options;

    public string ProviderName => "Yahoo Finance";

    public YahooFinanceMarketDataProvider(
        HttpClient http,
        IOptions<MarketDataOptions> options,
        ILogger<YahooFinanceMarketDataProvider> log)
    {
        _http = http;
        _log = log;
        _options = options.Value;
        if (_http.BaseAddress is null)
            _http.BaseAddress = new Uri("https://query1.finance.yahoo.com/");
        _http.DefaultRequestHeaders.UserAgent.ParseAdd("Mozilla/5.0 TradePerso/1.0");
    }

    public async Task<MarketQuote> GetQuoteAsync(string ticker, CancellationToken cancellationToken = default)
    {
        try
        {
            var url = $"v8/finance/chart/{Uri.EscapeDataString(ticker)}?range=2y&interval=1d";
            using var resp = await _http.GetAsync(url, cancellationToken);
            if (!resp.IsSuccessStatusCode)
                return EmptyQuote(ticker, $"HTTP {(int)resp.StatusCode}");

            var json = await resp.Content.ReadFromJsonAsync<JsonElement>(cancellationToken: cancellationToken);
            return ParseChart(ticker, json);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "Yahoo fetch failed for {Ticker}", ticker);
            return EmptyQuote(ticker, ex.Message);
        }
    }

    public async Task<IReadOnlyDictionary<string, MarketQuote>> GetQuotesAsync(
        IEnumerable<string> tickers, CancellationToken cancellationToken = default)
    {
        var list = tickers.Distinct(StringComparer.OrdinalIgnoreCase).ToList();
        var tasks = list.Select(t => GetQuoteAsync(t, cancellationToken));
        var results = await Task.WhenAll(tasks);
        return results.ToDictionary(r => r.Ticker, r => r, StringComparer.OrdinalIgnoreCase);
    }

    private static MarketQuote ParseChart(string ticker, JsonElement root)
    {
        try
        {
            var chart = root.GetProperty("chart");
            if (chart.TryGetProperty("error", out var err) && err.ValueKind != JsonValueKind.Null)
                return EmptyQuote(ticker, err.ToString());

            var result = chart.GetProperty("result")[0];
            var meta = result.GetProperty("meta");
            var currency = meta.TryGetProperty("currency", out var c) ? c.GetString() ?? "" : "";
            var timestamps = result.GetProperty("timestamp").EnumerateArray()
                .Select(t => DateTimeOffset.FromUnixTimeSeconds(t.GetInt64()).UtcDateTime)
                .ToList();
            var closes = result.GetProperty("indicators").GetProperty("quote")[0].GetProperty("close").EnumerateArray()
                .Select(v => v.ValueKind == JsonValueKind.Number ? (decimal?)v.GetDecimal() : null)
                .ToList();
            var volumes = result.GetProperty("indicators").GetProperty("quote")[0].GetProperty("volume").EnumerateArray()
                .Select(v => v.ValueKind == JsonValueKind.Number ? (decimal?)v.GetDecimal() : null)
                .ToList();

            var history = new List<HistoryPoint>(closes.Count);
            for (int i = 0; i < closes.Count; i++)
                if (closes[i].HasValue)
                    history.Add(new HistoryPoint(DateOnly.FromDateTime(timestamps[i]), closes[i]!.Value));

            decimal? price = history.Count > 0 ? history[^1].Close : null;
            decimal? change1d = history.Count >= 2 && history[^2].Close > 0
                ? (history[^1].Close - history[^2].Close) / history[^2].Close
                : null;
            decimal? Perf(int days) => PerfPct(history, days);
            decimal? ma50 = Sma(history, 50);
            decimal? ma200 = Sma(history, 200);
            decimal? rsi = Rsi(history, 14);
            decimal? vol = Volatility(history, 30);
            decimal? avgVol = volumes.Where(v => v.HasValue).TakeLast(20).Select(v => v!.Value).DefaultIfEmpty(0m).Average();

            return new MarketQuote(
                ticker, price, change1d,
                Perf(21), Perf(63), Perf(126), Perf(252),
                ma50, ma200, rsi, vol, avgVol,
                currency, "ok", null, DateTimeOffset.UtcNow, history);
        }
        catch (Exception ex)
        {
            return EmptyQuote(ticker, ex.Message);
        }
    }

    private static decimal? PerfPct(IReadOnlyList<HistoryPoint> h, int lookbackDays)
    {
        if (h.Count <= lookbackDays) return null;
        var prev = h[^Math.Min(lookbackDays + 1, h.Count)].Close;
        if (prev <= 0) return null;
        return (h[^1].Close - prev) / prev;
    }

    private static decimal? Sma(IReadOnlyList<HistoryPoint> h, int window)
    {
        if (h.Count < window) return null;
        decimal sum = 0;
        for (int i = h.Count - window; i < h.Count; i++) sum += h[i].Close;
        return sum / window;
    }

    private static decimal? Rsi(IReadOnlyList<HistoryPoint> h, int period)
    {
        if (h.Count <= period) return null;
        decimal gain = 0, loss = 0;
        for (int i = h.Count - period; i < h.Count; i++)
        {
            var diff = h[i].Close - h[i - 1].Close;
            if (diff >= 0) gain += diff; else loss -= diff;
        }
        if (loss == 0) return 100m;
        var rs = gain / loss;
        return 100m - (100m / (1m + rs));
    }

    private static decimal? Volatility(IReadOnlyList<HistoryPoint> h, int window)
    {
        if (h.Count <= window) return null;
        var returns = new List<double>(window);
        for (int i = h.Count - window; i < h.Count; i++)
        {
            var prev = h[i - 1].Close;
            if (prev > 0) returns.Add((double)((h[i].Close - prev) / prev));
        }
        if (returns.Count == 0) return null;
        var mean = returns.Average();
        var variance = returns.Sum(r => (r - mean) * (r - mean)) / returns.Count;
        var stdev = Math.Sqrt(variance);
        return (decimal)(stdev * Math.Sqrt(252.0));
    }

    private static MarketQuote EmptyQuote(string ticker, string err) => new(
        ticker, null, null, null, null, null, null, null, null, null, null, null,
        string.Empty, "error", err, DateTimeOffset.UtcNow, Array.Empty<HistoryPoint>());
}
