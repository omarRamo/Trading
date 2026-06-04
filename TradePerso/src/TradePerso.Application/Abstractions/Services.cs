using TradePerso.Application.DTOs;
using TradePerso.Domain.Entities;
using TradePerso.Domain.MarketData;

namespace TradePerso.Application.Abstractions;

public interface IPortfolioService
{
    Task<PortfolioSummaryDto> ComputeSummaryAsync(string userId, CancellationToken ct = default);
}

public interface IRecommendationService
{
    Task<IReadOnlyList<RecommendationDto>> GenerateAsync(string userId, CancellationToken ct = default);
}

public interface IMonthlyPlanService
{
    Task<MonthlyPlanResultDto> BuildAsync(string userId, CancellationToken ct = default);
}

public interface IBacktestService
{
    Task<BacktestResultDto> RunAsync(
        string ticker,
        DateOnly startDate,
        DateOnly endDate,
        decimal monthlyAmount,
        decimal initialCash,
        CancellationToken ct = default);
}

public interface IRiskService
{
    Task<IReadOnlyList<RiskAlertDto>> EvaluateAsync(string userId, CancellationToken ct = default);
}

public interface IPositionSizingService
{
    PositionSizingResultDto Compute(
        decimal portfolioValue,
        decimal riskPerTradePct,
        decimal entryPrice,
        decimal stopPrice,
        decimal? hardMaxPositionPct = null);
}

public interface IMarketSyncService
{
    Task<int> SyncAsync(string userId, CancellationToken ct = default);
    Task<bool> MaybeAutoSyncAsync(string userId, CancellationToken ct = default);
    Task<IReadOnlyDictionary<string, MarketQuote>> GetCachedQuotesAsync(
        string userId,
        IEnumerable<string> tickers,
        CancellationToken ct = default);
}

public interface ISeedService
{
    Task SeedDefaultsAsync(string userId, string email, CancellationToken ct = default);
}
