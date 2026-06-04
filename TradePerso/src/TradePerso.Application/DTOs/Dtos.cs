using TradePerso.Domain.Enums;

namespace TradePerso.Application.DTOs;

public sealed record PortfolioPositionDto(
    string Ticker,
    string Name,
    AssetType AssetType,
    string Sector,
    decimal Quantity,
    decimal AvgBuyPrice,
    decimal InvestedAmount,
    decimal? CurrentPrice,
    decimal CurrentValue,
    decimal Pnl,
    decimal PnlPct,
    decimal Weight);

public sealed record AllocationBreakdownDto(
    decimal EtfWeight,
    decimal StockWeight,
    decimal CashWeight,
    decimal TotalValue,
    decimal InvestedValue,
    decimal CashValue);

public sealed record PortfolioSummaryDto(
    IReadOnlyList<PortfolioPositionDto> Positions,
    AllocationBreakdownDto Current,
    AllocationBreakdownDto Target,
    AllocationBreakdownDto Gap,
    IReadOnlyDictionary<string, decimal> SectorExposure,
    decimal TotalInvested,
    decimal TotalCurrentValue,
    decimal TotalPnl,
    decimal TotalPnlPct);

public sealed record RecommendationDto(
    string Ticker,
    string Name,
    AssetType AssetType,
    string Sector,
    decimal? Price,
    decimal? Perf1m,
    decimal? Perf3m,
    decimal? Perf1y,
    decimal? Rsi14,
    decimal? Ma50,
    decimal? Ma200,
    decimal Score,
    PrudenceLevel Prudence,
    string Reasoning,
    bool AlreadyHeld);

public sealed record MonthlyPlanItemDto(
    string Bucket,
    string Ticker,
    string Name,
    decimal Amount,
    decimal? EstimatedShares,
    decimal Score,
    PrudenceLevel Prudence);

public sealed record MonthlyPlanResultDto(
    decimal MonthlyAmount,
    decimal EtfBudget,
    decimal StockBudget,
    decimal CashBudget,
    IReadOnlyList<MonthlyPlanItemDto> Items,
    IReadOnlyList<string> Warnings);

public sealed record BacktestPointDto(DateOnly Date, decimal DcaCurve, decimal MixedCurve, decimal LumpSumCurve);

public sealed record BacktestMetricsDto(
    decimal DcaInvested,
    decimal DcaFinalValue,
    decimal DcaCagr,
    decimal MixedFinalValue,
    decimal MixedCagr,
    decimal LumpSumFinalValue,
    decimal LumpSumCagr,
    decimal DcaMaxDrawdown);

public sealed record BacktestResultDto(
    IReadOnlyList<BacktestPointDto> Curve,
    BacktestMetricsDto Metrics,
    IReadOnlyList<string> Warnings);

public sealed record RiskAlertDto(string Severity, string Title, string Message);

public sealed record PositionSizingResultDto(
    decimal RiskAmount,
    decimal StopDistance,
    decimal Quantity,
    decimal NotionalValue,
    decimal PortfolioRiskPct,
    string? Warning);
