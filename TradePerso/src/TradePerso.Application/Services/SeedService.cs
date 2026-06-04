using TradePerso.Application.Abstractions;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Domain.Entities;
using TradePerso.Domain.Enums;

namespace TradePerso.Application.Services;

public sealed class SeedService : ISeedService
{
    private readonly IAssetRepository _assets;
    private readonly IUserSettingsRepository _settings;
    private readonly INotificationPreferencesRepository _prefs;

    public SeedService(
        IAssetRepository assets,
        IUserSettingsRepository settings,
        INotificationPreferencesRepository prefs)
    {
        _assets = assets;
        _settings = settings;
        _prefs = prefs;
    }

    public async Task SeedDefaultsAsync(string userId, string email, CancellationToken ct = default)
    {
        await _settings.GetOrCreateAsync(userId, ct);
        await _prefs.GetOrCreateAsync(userId, email, ct);

        var existing = await _assets.ListAsync(userId, ct: ct);
        if (existing.Count > 0) return;

        foreach (var a in DefaultWatchlist(userId))
            await _assets.UpsertAsync(a, ct);
    }

    private static IEnumerable<Asset> DefaultWatchlist(string userId)
    {
        var now = DateTimeOffset.UtcNow;
        Asset A(string ticker, string name, AssetType type, string currency, string sector, string region, string category)
            => new()
            {
                UserId = userId,
                Ticker = ticker,
                Name = name,
                AssetType = type,
                Currency = currency,
                Sector = sector,
                Region = region,
                Category = category,
                IsActive = true,
                RevolutAvailable = true,
                CreatedAt = now,
                UpdatedAt = now,
            };

        yield return A("VUSA.L", "Vanguard S&P 500 UCITS ETF", AssetType.Etf, "USD", "Broad market", "USA", "Core");
        yield return A("CSPX.L", "iShares Core S&P 500 UCITS ETF", AssetType.Etf, "USD", "Broad market", "USA", "Core");
        yield return A("EQQQ.L", "Invesco Nasdaq 100 UCITS ETF", AssetType.Etf, "USD", "Technology", "USA", "Sector");
        yield return A("IWDA.AS", "iShares Core MSCI World UCITS", AssetType.Etf, "USD", "Broad market", "World", "Core");
        yield return A("NVDA", "NVIDIA Corporation", AssetType.Stock, "USD", "Technology", "USA", "Growth");
        yield return A("MSFT", "Microsoft Corporation", AssetType.Stock, "USD", "Technology", "USA", "Quality");
        yield return A("AAPL", "Apple Inc.", AssetType.Stock, "USD", "Technology", "USA", "Quality");
        yield return A("GOOGL", "Alphabet Inc.", AssetType.Stock, "USD", "Technology", "USA", "Quality");
        yield return A("AMZN", "Amazon.com Inc.", AssetType.Stock, "USD", "Consumer", "USA", "Growth");
        yield return A("TSLA", "Tesla Inc.", AssetType.Stock, "USD", "Auto", "USA", "Growth");
        yield return A("ASML", "ASML Holding", AssetType.Stock, "EUR", "Technology", "Europe", "Quality");
        yield return A("MC.PA", "LVMH", AssetType.Stock, "EUR", "Luxury", "Europe", "Quality");
        yield return A("AIR.PA", "Airbus", AssetType.Stock, "EUR", "Industrial", "Europe", "Cyclical");
    }
}
