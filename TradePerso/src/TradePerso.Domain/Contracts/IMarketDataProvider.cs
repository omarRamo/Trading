using TradePerso.Domain.MarketData;

namespace TradePerso.Domain.Contracts;

/// <summary>
/// Provider abstraction so the market data source can be swapped (Yahoo, sample, future REST API, etc.).
/// </summary>
public interface IMarketDataProvider
{
    string ProviderName { get; }

    Task<MarketQuote> GetQuoteAsync(string ticker, CancellationToken cancellationToken = default);

    Task<IReadOnlyDictionary<string, MarketQuote>> GetQuotesAsync(
        IEnumerable<string> tickers,
        CancellationToken cancellationToken = default);
}
