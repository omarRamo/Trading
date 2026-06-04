using TradePerso.Domain.Entities;

namespace TradePerso.Application.Abstractions.Repositories;

public interface IUserSettingsRepository
{
    Task<UserSettings> GetOrCreateAsync(string userId, CancellationToken ct = default);
    Task UpdateAsync(UserSettings settings, CancellationToken ct = default);
}

public interface IAssetRepository
{
    Task<IReadOnlyList<Asset>> ListAsync(string userId, bool? activeOnly = null, CancellationToken ct = default);
    Task<Asset?> GetByTickerAsync(string userId, string ticker, CancellationToken ct = default);
    Task UpsertAsync(Asset asset, CancellationToken ct = default);
    Task SetActiveAsync(string userId, string ticker, bool isActive, CancellationToken ct = default);
}

public interface IPositionRepository
{
    Task<IReadOnlyList<Position>> ListAsync(string userId, CancellationToken ct = default);
    Task UpsertAsync(Position position, CancellationToken ct = default);
    Task DeleteAsync(string userId, string ticker, CancellationToken ct = default);
}

public interface ITransactionRepository
{
    Task<IReadOnlyList<Transaction>> ListAsync(string userId, CancellationToken ct = default);
    Task AddAsync(Transaction tx, CancellationToken ct = default);
    Task DeleteAsync(string userId, int id, CancellationToken ct = default);
}

public interface ITradeJournalRepository
{
    Task<IReadOnlyList<TradeJournalEntry>> ListAsync(string userId, CancellationToken ct = default);
    Task AddAsync(TradeJournalEntry entry, CancellationToken ct = default);
    Task UpdateAsync(TradeJournalEntry entry, CancellationToken ct = default);
    Task DeleteAsync(string userId, int id, CancellationToken ct = default);
}

public interface INotificationPreferencesRepository
{
    Task<NotificationPreferences> GetOrCreateAsync(string userId, string email, CancellationToken ct = default);
    Task UpsertAsync(NotificationPreferences prefs, CancellationToken ct = default);
}

public interface IRecommendationRunRepository
{
    Task SaveAsync(RecommendationRun run, CancellationToken ct = default);
    Task<RecommendationRun?> GetLatestAsync(string userId, CancellationToken ct = default);
}

public interface IMonthlyPlanRepository
{
    Task SaveAsync(MonthlyPlanEntry entry, CancellationToken ct = default);
    Task<MonthlyPlanEntry?> GetLatestAsync(string userId, CancellationToken ct = default);
}
