using Microsoft.Extensions.Caching.Memory;
using TradePerso.Application.Abstractions;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Domain.Contracts;
using TradePerso.Domain.MarketData;

namespace TradePerso.Application.Services;

public sealed class MarketSyncService : IMarketSyncService
{
    private readonly IMarketDataProvider _provider;
    private readonly IAssetRepository _assets;
    private readonly IPositionRepository _positions;
    private readonly IUserSettingsRepository _settings;
    private readonly IMemoryCache _cache;
    private static readonly TimeSpan CacheDuration = TimeSpan.FromMinutes(15);

    public MarketSyncService(
        IMarketDataProvider provider,
        IAssetRepository assets,
        IPositionRepository positions,
        IUserSettingsRepository settings,
        IMemoryCache cache)
    {
        _provider = provider;
        _assets = assets;
        _positions = positions;
        _settings = settings;
        _cache = cache;
    }

    public async Task<int> SyncAsync(string userId, CancellationToken ct = default)
    {
        var tickers = await GetUserTickersAsync(userId, ct);
        if (tickers.Count == 0) return 0;

        var quotes = await _provider.GetQuotesAsync(tickers, ct);
        foreach (var (ticker, quote) in quotes)
        {
            _cache.Set(CacheKey(ticker), quote, CacheDuration);
        }

        var settings = await _settings.GetOrCreateAsync(userId, ct);
        settings.LastMarketSyncAt = DateTimeOffset.UtcNow;
        await _settings.UpdateAsync(settings, ct);
        return quotes.Count;
    }

    public async Task<bool> MaybeAutoSyncAsync(string userId, CancellationToken ct = default)
    {
        var settings = await _settings.GetOrCreateAsync(userId, ct);
        if (!settings.AutoSyncMarketData) return false;
        var threshold = TimeSpan.FromHours(settings.AutoSyncIntervalHours);
        if (settings.LastMarketSyncAt is DateTimeOffset last && DateTimeOffset.UtcNow - last < threshold) return false;
        await SyncAsync(userId, ct);
        return true;
    }

    public async Task<IReadOnlyDictionary<string, MarketQuote>> GetCachedQuotesAsync(
        string userId, IEnumerable<string> tickers, CancellationToken ct = default)
    {
        var result = new Dictionary<string, MarketQuote>(StringComparer.OrdinalIgnoreCase);
        var missing = new List<string>();
        foreach (var t in tickers.Distinct(StringComparer.OrdinalIgnoreCase))
        {
            if (_cache.TryGetValue(CacheKey(t), out MarketQuote? cached) && cached is not null)
                result[t] = cached;
            else
                missing.Add(t);
        }

        if (missing.Count > 0)
        {
            var fetched = await _provider.GetQuotesAsync(missing, ct);
            foreach (var (k, v) in fetched)
            {
                _cache.Set(CacheKey(k), v, CacheDuration);
                result[k] = v;
            }
        }
        return result;
    }

    private async Task<List<string>> GetUserTickersAsync(string userId, CancellationToken ct)
    {
        var assets = await _assets.ListAsync(userId, activeOnly: true, ct);
        var positions = await _positions.ListAsync(userId, ct);
        return assets.Select(a => a.Ticker)
            .Concat(positions.Select(p => p.Ticker))
            .Where(t => !string.IsNullOrWhiteSpace(t))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    private static string CacheKey(string ticker) => $"quote::{ticker.ToUpperInvariant()}";
}
