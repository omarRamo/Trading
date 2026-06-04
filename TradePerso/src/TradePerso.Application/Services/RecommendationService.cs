using TradePerso.Application.Abstractions;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Application.DTOs;
using TradePerso.Domain.Entities;
using TradePerso.Domain.Enums;
using TradePerso.Domain.MarketData;

namespace TradePerso.Application.Services;

public sealed class RecommendationService : IRecommendationService
{
    private readonly IAssetRepository _assets;
    private readonly IPositionRepository _positions;
    private readonly IUserSettingsRepository _settings;
    private readonly IMarketSyncService _marketSync;

    public RecommendationService(
        IAssetRepository assets,
        IPositionRepository positions,
        IUserSettingsRepository settings,
        IMarketSyncService marketSync)
    {
        _assets = assets;
        _positions = positions;
        _settings = settings;
        _marketSync = marketSync;
    }

    public async Task<IReadOnlyList<RecommendationDto>> GenerateAsync(string userId, CancellationToken ct = default)
    {
        var assets = (await _assets.ListAsync(userId, activeOnly: true, ct)).ToList();
        if (assets.Count == 0) return Array.Empty<RecommendationDto>();

        var positions = await _positions.ListAsync(userId, ct);
        var heldTickers = positions.Select(p => p.Ticker).ToHashSet(StringComparer.OrdinalIgnoreCase);

        var tickers = assets.Select(a => a.Ticker).ToList();
        var quotes = await _marketSync.GetCachedQuotesAsync(userId, tickers, ct);

        var settings = await _settings.GetOrCreateAsync(userId, ct);
        var result = new List<RecommendationDto>();

        foreach (var asset in assets)
        {
            quotes.TryGetValue(asset.Ticker, out var q);
            var (score, prudence, reasoning) = Score(asset, q, settings);
            result.Add(new RecommendationDto(
                asset.Ticker, asset.Name, asset.AssetType, asset.Sector,
                q?.Price, q?.Perf1m, q?.Perf3m, q?.Perf1y, q?.Rsi14, q?.Ma50, q?.Ma200,
                score, prudence, reasoning, heldTickers.Contains(asset.Ticker)));
        }

        return result
            .OrderByDescending(r => r.Score)
            .ThenBy(r => r.Ticker)
            .ToList();
    }

    private static (decimal Score, PrudenceLevel Prudence, string Reasoning) Score(
        Asset asset, MarketQuote? q, UserSettings settings)
    {
        decimal score = 50m;
        var reasons = new List<string>();

        if (q is null || q.Price is null)
        {
            return (40m, PrudenceLevel.Wait, "No market data available.");
        }

        // Trend filter on 50/200 SMA.
        if (q.Ma50.HasValue && q.Ma200.HasValue && q.Price.HasValue)
        {
            if (q.Price > q.Ma50 && q.Ma50 > q.Ma200) { score += 12; reasons.Add("Uptrend (price > MA50 > MA200)"); }
            else if (q.Price < q.Ma200) { score -= 12; reasons.Add("Below MA200"); }
        }

        // Momentum.
        if (q.Perf3m.HasValue)
        {
            if (q.Perf3m > 0.05m) { score += 8; reasons.Add("Positive 3M momentum"); }
            else if (q.Perf3m < -0.10m) { score -= 8; reasons.Add("Weak 3M momentum"); }
        }
        if (q.Perf1y.HasValue)
        {
            if (q.Perf1y > 0.15m) { score += 6; reasons.Add("Strong 1Y momentum"); }
            else if (q.Perf1y < -0.10m) { score -= 6; reasons.Add("Negative 1Y momentum"); }
        }

        // RSI.
        if (q.Rsi14.HasValue)
        {
            if (q.Rsi14 < 30) { score += 6; reasons.Add("Oversold (RSI < 30)"); }
            else if (q.Rsi14 > 75) { score -= 10; reasons.Add("Overbought (RSI > 75)"); }
        }

        // ETF bias depending on risk profile.
        if (asset.AssetType == AssetType.Etf)
        {
            score += settings.RiskProfile switch
            {
                RiskProfile.Conservative => 8m,
                RiskProfile.Balanced => 4m,
                _ => 0m,
            };
        }
        else if (asset.AssetType == AssetType.Stock && settings.RiskProfile == RiskProfile.Conservative)
        {
            score -= 4m;
        }

        score = Math.Clamp(score, 0m, 100m);
        var prudence = score switch
        {
            >= 75m => PrudenceLevel.Interesting,
            >= 60m => PrudenceLevel.Watch,
            >= 45m => PrudenceLevel.Wait,
            _ => PrudenceLevel.Avoid,
        };

        var reasoning = reasons.Count == 0 ? "Neutral signal." : string.Join("; ", reasons) + ".";
        return (Math.Round(score, 1), prudence, reasoning);
    }
}
