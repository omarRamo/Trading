using TradePerso.Application.Abstractions;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Application.DTOs;
using TradePerso.Domain.Enums;

namespace TradePerso.Application.Services;

public sealed class RiskService : IRiskService
{
    private readonly IPortfolioService _portfolio;
    private readonly IUserSettingsRepository _settings;

    public RiskService(IPortfolioService portfolio, IUserSettingsRepository settings)
    {
        _portfolio = portfolio;
        _settings = settings;
    }

    public async Task<IReadOnlyList<RiskAlertDto>> EvaluateAsync(string userId, CancellationToken ct = default)
    {
        var summary = await _portfolio.ComputeSummaryAsync(userId, ct);
        var settings = await _settings.GetOrCreateAsync(userId, ct);
        var alerts = new List<RiskAlertDto>();

        foreach (var p in summary.Positions)
        {
            if (p.Weight > settings.HardMaxIndividualPosition)
                alerts.Add(new RiskAlertDto("error",
                    $"Concentration: {p.Ticker}",
                    $"{p.Ticker} weighs {p.Weight:P1}, above hard cap {settings.HardMaxIndividualPosition:P0}."));
            else if (p.Weight > settings.MaxIndividualPosition)
                alerts.Add(new RiskAlertDto("warning",
                    $"Above target: {p.Ticker}",
                    $"{p.Ticker} weighs {p.Weight:P1}, target max {settings.MaxIndividualPosition:P0}."));
        }

        var techWeight = summary.Positions
            .Where(p => p.Sector.Contains("Tech", StringComparison.OrdinalIgnoreCase))
            .Sum(p => p.Weight);
        if (techWeight > settings.TechExposureLimit)
            alerts.Add(new RiskAlertDto("warning", "Tech exposure",
                $"Technology exposure is {techWeight:P1}, above limit {settings.TechExposureLimit:P0}."));

        if (Math.Abs(summary.Gap.EtfWeight) > 0.10m)
            alerts.Add(new RiskAlertDto("info", "Allocation drift",
                $"ETF allocation drift {summary.Gap.EtfWeight:P1} vs target."));

        if (summary.Current.CashWeight < settings.TargetAllocationCash / 2m)
            alerts.Add(new RiskAlertDto("info", "Low cash buffer",
                $"Cash reserve is {summary.Current.CashWeight:P1}, below half of target {settings.TargetAllocationCash:P0}."));

        return alerts;
    }
}

public sealed class PositionSizingService : IPositionSizingService
{
    public PositionSizingResultDto Compute(
        decimal portfolioValue,
        decimal riskPerTradePct,
        decimal entryPrice,
        decimal stopPrice,
        decimal? hardMaxPositionPct = null)
    {
        if (portfolioValue <= 0 || entryPrice <= 0)
            return new PositionSizingResultDto(0, 0, 0, 0, 0, "Portfolio value and entry price must be positive.");

        var stopDistance = Math.Abs(entryPrice - stopPrice);
        if (stopDistance <= 0)
            return new PositionSizingResultDto(0, 0, 0, 0, 0, "Stop must differ from entry price.");

        var riskAmount = portfolioValue * riskPerTradePct;
        var qty = Math.Floor(riskAmount / stopDistance);
        var notional = qty * entryPrice;
        var portfolioRiskPct = notional / portfolioValue;

        string? warning = null;
        if (hardMaxPositionPct is decimal cap && portfolioRiskPct > cap)
            warning = $"Notional exceeds hard cap {cap:P0}; size will be reduced.";

        return new PositionSizingResultDto(
            Math.Round(riskAmount, 2),
            Math.Round(stopDistance, 4),
            qty,
            Math.Round(notional, 2),
            Math.Round(portfolioRiskPct, 4),
            warning);
    }
}
