using TradePerso.Application.Abstractions;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Application.DTOs;
using TradePerso.Domain.Entities;
using TradePerso.Domain.Enums;
using TradePerso.Domain.MarketData;

namespace TradePerso.Application.Services;

public sealed class PortfolioService : IPortfolioService
{
    private readonly IPositionRepository _positions;
    private readonly IUserSettingsRepository _settings;
    private readonly IMarketSyncService _marketSync;

    public PortfolioService(
        IPositionRepository positions,
        IUserSettingsRepository settings,
        IMarketSyncService marketSync)
    {
        _positions = positions;
        _settings = settings;
        _marketSync = marketSync;
    }

    public async Task<PortfolioSummaryDto> ComputeSummaryAsync(string userId, CancellationToken ct = default)
    {
        var positions = await _positions.ListAsync(userId, ct);
        var settings = await _settings.GetOrCreateAsync(userId, ct);

        var tickers = positions.Select(p => p.Ticker).Distinct(StringComparer.OrdinalIgnoreCase).ToList();
        var quotes = tickers.Count == 0
            ? new Dictionary<string, MarketQuote>(StringComparer.OrdinalIgnoreCase)
            : (await _marketSync.GetCachedQuotesAsync(userId, tickers, ct))
              .ToDictionary(kv => kv.Key, kv => kv.Value, StringComparer.OrdinalIgnoreCase);

        var rows = new List<PortfolioPositionDto>();
        decimal investedTotal = 0;
        decimal currentTotal = 0;

        foreach (var p in positions)
        {
            decimal invested = p.InvestedAmount > 0 ? p.InvestedAmount : p.AvgBuyPrice * p.Quantity + p.Fees;
            decimal? price = quotes.TryGetValue(p.Ticker, out var q) ? q.Price : null;
            decimal currentValue = price.HasValue ? price.Value * p.Quantity : invested;
            decimal pnl = currentValue - invested;
            decimal pnlPct = invested > 0 ? pnl / invested : 0m;

            rows.Add(new PortfolioPositionDto(
                p.Ticker, p.Name, p.AssetType, p.Sector,
                p.Quantity, p.AvgBuyPrice, invested, price,
                currentValue, pnl, pnlPct, 0m));

            investedTotal += invested;
            currentTotal += currentValue;
        }

        var totalWithCash = currentTotal + settings.CashAvailable;
        var rowsWithWeights = rows
            .Select(r => r with { Weight = totalWithCash > 0 ? r.CurrentValue / totalWithCash : 0m })
            .ToList();

        decimal etfValue = rowsWithWeights.Where(r => r.AssetType == AssetType.Etf).Sum(r => r.CurrentValue);
        decimal stockValue = rowsWithWeights.Where(r => r.AssetType == AssetType.Stock).Sum(r => r.CurrentValue);
        decimal cashValue = settings.CashAvailable;
        decimal denom = totalWithCash > 0 ? totalWithCash : 1m;

        var current = new AllocationBreakdownDto(
            etfValue / denom, stockValue / denom, cashValue / denom,
            totalWithCash, investedTotal, cashValue);

        var target = new AllocationBreakdownDto(
            settings.TargetAllocationEtf, settings.TargetAllocationStocks, settings.TargetAllocationCash,
            totalWithCash,
            settings.TargetAllocationEtf * totalWithCash + settings.TargetAllocationStocks * totalWithCash,
            settings.TargetAllocationCash * totalWithCash);

        var gap = new AllocationBreakdownDto(
            target.EtfWeight - current.EtfWeight,
            target.StockWeight - current.StockWeight,
            target.CashWeight - current.CashWeight,
            0m, 0m, 0m);

        var sectorExposure = rowsWithWeights
            .Where(r => !string.IsNullOrWhiteSpace(r.Sector))
            .GroupBy(r => r.Sector, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(g => g.Key, g => g.Sum(x => x.Weight), StringComparer.OrdinalIgnoreCase);

        decimal totalPnl = currentTotal - investedTotal;
        decimal totalPnlPct = investedTotal > 0 ? totalPnl / investedTotal : 0m;

        return new PortfolioSummaryDto(
            rowsWithWeights, current, target, gap, sectorExposure,
            investedTotal, currentTotal, totalPnl, totalPnlPct);
    }
}
