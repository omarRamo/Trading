using TradePerso.Application.Abstractions;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Application.DTOs;
using TradePerso.Domain.Enums;

namespace TradePerso.Application.Services;

public sealed class MonthlyPlanService : IMonthlyPlanService
{
    private readonly IRecommendationService _recommendations;
    private readonly IUserSettingsRepository _settings;

    public MonthlyPlanService(IRecommendationService recommendations, IUserSettingsRepository settings)
    {
        _recommendations = recommendations;
        _settings = settings;
    }

    public async Task<MonthlyPlanResultDto> BuildAsync(string userId, CancellationToken ct = default)
    {
        var settings = await _settings.GetOrCreateAsync(userId, ct);
        var monthly = settings.MonthlyInvestment;
        var etfBudget = Math.Round(monthly * settings.TargetAllocationEtf, 2);
        var stockBudget = Math.Round(monthly * settings.TargetAllocationStocks, 2);
        var cashBudget = Math.Round(monthly - etfBudget - stockBudget, 2);

        var recos = await _recommendations.GenerateAsync(userId, ct);
        var warnings = new List<string>();
        var items = new List<MonthlyPlanItemDto>();

        var etfPicks = recos
            .Where(r => r.AssetType == AssetType.Etf && r.Prudence != PrudenceLevel.Avoid)
            .Take(3).ToList();
        var stockPicks = recos
            .Where(r => r.AssetType == AssetType.Stock && r.Prudence is PrudenceLevel.Interesting or PrudenceLevel.Watch)
            .Take(3).ToList();

        AllocateBucket("ETF (70%)", etfBudget, etfPicks, items, warnings);
        AllocateBucket("Stocks (20%)", stockBudget, stockPicks, items, warnings);

        if (cashBudget > 0)
            items.Add(new MonthlyPlanItemDto("Cash (10%)", "CASH", "Cash reserve", cashBudget, null, 0m, PrudenceLevel.Watch));

        return new MonthlyPlanResultDto(monthly, etfBudget, stockBudget, cashBudget, items, warnings);
    }

    private static void AllocateBucket(
        string bucket,
        decimal budget,
        IReadOnlyList<RecommendationDto> picks,
        List<MonthlyPlanItemDto> items,
        List<string> warnings)
    {
        if (budget <= 0) return;
        if (picks.Count == 0)
        {
            warnings.Add($"No eligible {bucket} candidates found this month.");
            return;
        }

        var slice = Math.Round(budget / picks.Count, 2);
        foreach (var p in picks)
        {
            decimal? shares = p.Price is > 0 ? Math.Round(slice / p.Price.Value, 4) : null;
            items.Add(new MonthlyPlanItemDto(bucket, p.Ticker, p.Name, slice, shares, p.Score, p.Prudence));
        }
    }
}
