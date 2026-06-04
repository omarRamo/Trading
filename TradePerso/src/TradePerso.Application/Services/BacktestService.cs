using TradePerso.Application.Abstractions;
using TradePerso.Application.DTOs;
using TradePerso.Domain.Contracts;

namespace TradePerso.Application.Services;

public sealed class BacktestService : IBacktestService
{
    private readonly IMarketDataProvider _marketData;

    public BacktestService(IMarketDataProvider marketData) => _marketData = marketData;

    public async Task<BacktestResultDto> RunAsync(
        string ticker,
        DateOnly startDate,
        DateOnly endDate,
        decimal monthlyAmount,
        decimal initialCash,
        CancellationToken ct = default)
    {
        var warnings = new List<string>();
        var quote = await _marketData.GetQuoteAsync(ticker, ct);
        var history = quote.History
            .Where(h => h.Date >= startDate && h.Date <= endDate)
            .OrderBy(h => h.Date)
            .ToList();

        if (history.Count < 2)
        {
            warnings.Add("Not enough historical data for the selected range.");
            return new BacktestResultDto(
                Array.Empty<BacktestPointDto>(),
                new BacktestMetricsDto(0,0,0,0,0,0,0,0),
                warnings);
        }

        // Group monthly: take first trading day of each month.
        var monthly = history
            .GroupBy(h => new { h.Date.Year, h.Date.Month })
            .Select(g => g.OrderBy(x => x.Date).First())
            .OrderBy(x => x.Date)
            .ToList();

        decimal dcaShares = 0, dcaInvested = 0;
        decimal mixedShares = initialCash * 0.7m / monthly[0].Close;
        decimal mixedRemaining = initialCash * 0.3m;
        decimal mixedInvested = initialCash;
        decimal lumpShares = initialCash > 0 ? initialCash / monthly[0].Close : 0m;
        decimal lumpInvested = initialCash;

        var curve = new List<BacktestPointDto>();
        decimal peakDca = 0, maxDdDca = 0;

        for (int i = 0; i < monthly.Count; i++)
        {
            var pt = monthly[i];
            // DCA
            dcaShares += monthlyAmount / pt.Close;
            dcaInvested += monthlyAmount;

            // 70/20/10 (already invested 70% lump; deploy 10% of remaining monthly cash each month)
            if (mixedRemaining > 0)
            {
                var deploy = Math.Min(mixedRemaining, monthlyAmount * 0.20m);
                mixedShares += deploy / pt.Close;
                mixedRemaining -= deploy;
            }
            mixedShares += monthlyAmount * 0.80m / pt.Close;
            mixedInvested += monthlyAmount;

            var dcaValue = dcaShares * pt.Close;
            var mixedValue = mixedShares * pt.Close + mixedRemaining;
            var lumpValue = lumpShares * pt.Close;

            peakDca = Math.Max(peakDca, dcaValue);
            if (peakDca > 0)
            {
                var dd = (peakDca - dcaValue) / peakDca;
                if (dd > maxDdDca) maxDdDca = dd;
            }

            curve.Add(new BacktestPointDto(pt.Date, Round(dcaValue), Round(mixedValue), Round(lumpValue)));
        }

        decimal years = Math.Max(0.1m, (decimal)(monthly[^1].Date.ToDateTime(TimeOnly.MinValue) - monthly[0].Date.ToDateTime(TimeOnly.MinValue)).TotalDays / 365.25m);
        var last = curve[^1];

        var metrics = new BacktestMetricsDto(
            Round(dcaInvested),
            last.DcaCurve,
            Cagr(last.DcaCurve, dcaInvested, years),
            last.MixedCurve,
            Cagr(last.MixedCurve, mixedInvested, years),
            last.LumpSumCurve,
            Cagr(last.LumpSumCurve, lumpInvested, years),
            Math.Round(maxDdDca, 4));

        return new BacktestResultDto(curve, metrics, warnings);
    }

    private static decimal Cagr(decimal finalValue, decimal invested, decimal years)
    {
        if (invested <= 0 || finalValue <= 0 || years <= 0) return 0m;
        var ratio = (double)finalValue / (double)invested;
        var cagr = Math.Pow(ratio, 1.0 / (double)years) - 1.0;
        return Math.Round((decimal)cagr, 4);
    }

    private static decimal Round(decimal v) => Math.Round(v, 2);
}
