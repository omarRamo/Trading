namespace TradePerso.Infrastructure.MarketData;

public sealed class MarketDataOptions
{
    public const string SectionName = "MarketData";

    /// <summary>"Yahoo" or "Sample". Drives which IMarketDataProvider implementation is registered.</summary>
    public string Provider { get; set; } = "Yahoo";

    public int HistoryDays { get; set; } = 400;
}
