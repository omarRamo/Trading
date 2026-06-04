using TradePerso.Domain.Enums;

namespace TradePerso.Domain.Entities;

public class AppUser
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string Email { get; set; } = string.Empty;
    public string? DisplayName { get; set; }
    public string? PictureUrl { get; set; }
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? LastLoginAt { get; set; }
}

public class UserSettings
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public AppLanguage Language { get; set; } = AppLanguage.English;
    public string BaseCurrency { get; set; } = "EUR";
    public decimal CapitalTotal { get; set; }
    public decimal CashAvailable { get; set; }
    public decimal MonthlyInvestment { get; set; } = 1000m;
    public decimal TargetAllocationEtf { get; set; } = 0.70m;
    public decimal TargetAllocationStocks { get; set; } = 0.20m;
    public decimal TargetAllocationCash { get; set; } = 0.10m;
    public decimal MaxIndividualPosition { get; set; } = 0.08m;
    public decimal HardMaxIndividualPosition { get; set; } = 0.10m;
    public decimal TechExposureLimit { get; set; } = 0.45m;
    public decimal CorrelationWarningThreshold { get; set; } = 0.85m;
    public RiskProfile RiskProfile { get; set; } = RiskProfile.Balanced;
    public string InvestmentHorizon { get; set; } = "long term";
    public bool AutoSyncMarketData { get; set; } = true;
    public int AutoSyncIntervalHours { get; set; } = 6;
    public DateTimeOffset? LastMarketSyncAt { get; set; }
    public decimal RiskPerTradePct { get; set; } = 0.01m;
    public decimal DefaultRrTarget { get; set; } = 2.0m;
    public string MarketDataProvider { get; set; } = "Yahoo";
}

public class Asset
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public string Ticker { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public AssetType AssetType { get; set; }
    public string Currency { get; set; } = "EUR";
    public string Sector { get; set; } = string.Empty;
    public string Region { get; set; } = string.Empty;
    public string Category { get; set; } = string.Empty;
    public bool IsActive { get; set; } = true;
    public bool RevolutAvailable { get; set; } = true;
    public string? Notes { get; set; }
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public class Position
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public string Ticker { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public AssetType AssetType { get; set; }
    public decimal Quantity { get; set; }
    public decimal AvgBuyPrice { get; set; }
    public DateTime PurchaseDate { get; set; } = DateTime.UtcNow.Date;
    public string Currency { get; set; } = "EUR";
    public decimal InvestedAmount { get; set; }
    public decimal Fees { get; set; }
    public string Sector { get; set; } = string.Empty;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public class Transaction
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public string Ticker { get; set; } = string.Empty;
    public string AssetName { get; set; } = string.Empty;
    public AssetType AssetType { get; set; }
    public TransactionType TransactionType { get; set; }
    public decimal Quantity { get; set; }
    public decimal Price { get; set; }
    public DateTime TransactionDate { get; set; } = DateTime.UtcNow.Date;
    public string Currency { get; set; } = "EUR";
    public decimal Fees { get; set; }
    public decimal Amount { get; set; }
    public string? Notes { get; set; }
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public class RecommendationRun
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public DateTimeOffset RunAt { get; set; } = DateTimeOffset.UtcNow;
    public string PayloadJson { get; set; } = "[]";
    public string SummaryJson { get; set; } = "{}";
}

public class MonthlyPlanEntry
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public DateTime PlanDate { get; set; } = DateTime.UtcNow.Date;
    public decimal MonthlyAmount { get; set; }
    public decimal EtfAmount { get; set; }
    public decimal StockAmount { get; set; }
    public decimal CashAmount { get; set; }
    public string DetailsJson { get; set; } = "[]";
    public string WarningsJson { get; set; } = "[]";
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public class TradeJournalEntry
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public string Ticker { get; set; } = string.Empty;
    public TradeDirection Direction { get; set; } = TradeDirection.Long;
    public string SetupTag { get; set; } = string.Empty;
    public string? Thesis { get; set; }
    public string? Invalidation { get; set; }
    public decimal? EntryPrice { get; set; }
    public decimal? StopLoss { get; set; }
    public decimal? TargetPrice { get; set; }
    public decimal? RiskAmount { get; set; }
    public decimal? PlannedRr { get; set; }
    public decimal? RealizedPnl { get; set; }
    public decimal? RealizedR { get; set; }
    public TradeStatus Status { get; set; } = TradeStatus.Open;
    public DateTime OpenedAt { get; set; } = DateTime.UtcNow.Date;
    public DateTime? ClosedAt { get; set; }
    public string? Notes { get; set; }
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public class NotificationPreferences
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public bool IsEnabled { get; set; }
    public decimal MinScore { get; set; } = 60m;
    public string AssetTypesCsv { get; set; } = "Etf,Stock";
    public int MaxItems { get; set; } = 10;
    public string Frequency { get; set; } = "manual";
    public int SendHourUtc { get; set; } = 7;
    public DateTimeOffset? LastSentAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; } = DateTimeOffset.UtcNow;
}

public class PriceAlert
{
    public int Id { get; set; }
    public string UserId { get; set; } = string.Empty;
    public string Ticker { get; set; } = string.Empty;
    public string AlertType { get; set; } = "above";
    public decimal Threshold { get; set; }
    public bool IsActive { get; set; } = true;
    public DateTimeOffset CreatedAt { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset? TriggeredAt { get; set; }
}
