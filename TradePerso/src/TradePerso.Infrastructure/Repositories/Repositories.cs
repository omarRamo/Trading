using Microsoft.EntityFrameworkCore;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Domain.Entities;
using TradePerso.Infrastructure.Persistence;

namespace TradePerso.Infrastructure.Repositories;

public sealed class UserSettingsRepository : IUserSettingsRepository
{
    private readonly TradePersoDbContext _db;
    public UserSettingsRepository(TradePersoDbContext db) => _db = db;

    public async Task<UserSettings> GetOrCreateAsync(string userId, CancellationToken ct = default)
    {
        var s = await _db.UserSettings.FirstOrDefaultAsync(x => x.UserId == userId, ct);
        if (s is not null) return s;
        s = new UserSettings { UserId = userId };
        _db.UserSettings.Add(s);
        await _db.SaveChangesAsync(ct);
        return s;
    }

    public async Task UpdateAsync(UserSettings settings, CancellationToken ct = default)
    {
        _db.UserSettings.Update(settings);
        await _db.SaveChangesAsync(ct);
    }
}

public sealed class AssetRepository : IAssetRepository
{
    private readonly TradePersoDbContext _db;
    public AssetRepository(TradePersoDbContext db) => _db = db;

    public async Task<IReadOnlyList<Asset>> ListAsync(string userId, bool? activeOnly = null, CancellationToken ct = default)
    {
        var q = _db.Assets.AsNoTracking().Where(a => a.UserId == userId);
        if (activeOnly == true) q = q.Where(a => a.IsActive);
        return await q.OrderBy(a => a.Ticker).ToListAsync(ct);
    }

    public Task<Asset?> GetByTickerAsync(string userId, string ticker, CancellationToken ct = default)
        => _db.Assets.FirstOrDefaultAsync(a => a.UserId == userId && a.Ticker == ticker, ct);

    public async Task UpsertAsync(Asset asset, CancellationToken ct = default)
    {
        var existing = await _db.Assets.FirstOrDefaultAsync(
            a => a.UserId == asset.UserId && a.Ticker == asset.Ticker, ct);
        if (existing is null)
        {
            _db.Assets.Add(asset);
        }
        else
        {
            existing.Name = asset.Name;
            existing.AssetType = asset.AssetType;
            existing.Currency = asset.Currency;
            existing.Sector = asset.Sector;
            existing.Region = asset.Region;
            existing.Category = asset.Category;
            existing.IsActive = asset.IsActive;
            existing.RevolutAvailable = asset.RevolutAvailable;
            existing.Notes = asset.Notes;
            existing.UpdatedAt = DateTimeOffset.UtcNow;
        }
        await _db.SaveChangesAsync(ct);
    }

    public async Task SetActiveAsync(string userId, string ticker, bool isActive, CancellationToken ct = default)
    {
        var a = await _db.Assets.FirstOrDefaultAsync(x => x.UserId == userId && x.Ticker == ticker, ct);
        if (a is null) return;
        a.IsActive = isActive;
        a.UpdatedAt = DateTimeOffset.UtcNow;
        await _db.SaveChangesAsync(ct);
    }
}

public sealed class PositionRepository : IPositionRepository
{
    private readonly TradePersoDbContext _db;
    public PositionRepository(TradePersoDbContext db) => _db = db;

    public async Task<IReadOnlyList<Position>> ListAsync(string userId, CancellationToken ct = default)
        => await _db.Positions.AsNoTracking().Where(p => p.UserId == userId)
            .OrderBy(p => p.Ticker).ToListAsync(ct);

    public async Task UpsertAsync(Position position, CancellationToken ct = default)
    {
        var existing = await _db.Positions.FirstOrDefaultAsync(
            p => p.UserId == position.UserId && p.Ticker == position.Ticker, ct);
        if (existing is null)
        {
            _db.Positions.Add(position);
        }
        else
        {
            existing.Name = position.Name;
            existing.AssetType = position.AssetType;
            existing.Quantity = position.Quantity;
            existing.AvgBuyPrice = position.AvgBuyPrice;
            existing.PurchaseDate = position.PurchaseDate;
            existing.Currency = position.Currency;
            existing.InvestedAmount = position.InvestedAmount;
            existing.Fees = position.Fees;
            existing.Sector = position.Sector;
            existing.UpdatedAt = DateTimeOffset.UtcNow;
        }
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteAsync(string userId, string ticker, CancellationToken ct = default)
    {
        var p = await _db.Positions.FirstOrDefaultAsync(x => x.UserId == userId && x.Ticker == ticker, ct);
        if (p is null) return;
        _db.Positions.Remove(p);
        await _db.SaveChangesAsync(ct);
    }
}

public sealed class TransactionRepository : ITransactionRepository
{
    private readonly TradePersoDbContext _db;
    public TransactionRepository(TradePersoDbContext db) => _db = db;

    public async Task<IReadOnlyList<Transaction>> ListAsync(string userId, CancellationToken ct = default)
        => await _db.Transactions.AsNoTracking().Where(t => t.UserId == userId)
            .OrderByDescending(t => t.TransactionDate).ThenByDescending(t => t.Id).ToListAsync(ct);

    public async Task AddAsync(Transaction tx, CancellationToken ct = default)
    {
        _db.Transactions.Add(tx);
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteAsync(string userId, int id, CancellationToken ct = default)
    {
        var t = await _db.Transactions.FirstOrDefaultAsync(x => x.UserId == userId && x.Id == id, ct);
        if (t is null) return;
        _db.Transactions.Remove(t);
        await _db.SaveChangesAsync(ct);
    }
}

public sealed class TradeJournalRepository : ITradeJournalRepository
{
    private readonly TradePersoDbContext _db;
    public TradeJournalRepository(TradePersoDbContext db) => _db = db;

    public async Task<IReadOnlyList<TradeJournalEntry>> ListAsync(string userId, CancellationToken ct = default)
        => await _db.TradeJournalEntries.AsNoTracking().Where(e => e.UserId == userId)
            .OrderByDescending(e => e.OpenedAt).ThenByDescending(e => e.Id).ToListAsync(ct);

    public async Task AddAsync(TradeJournalEntry entry, CancellationToken ct = default)
    {
        _db.TradeJournalEntries.Add(entry);
        await _db.SaveChangesAsync(ct);
    }

    public async Task UpdateAsync(TradeJournalEntry entry, CancellationToken ct = default)
    {
        entry.UpdatedAt = DateTimeOffset.UtcNow;
        _db.TradeJournalEntries.Update(entry);
        await _db.SaveChangesAsync(ct);
    }

    public async Task DeleteAsync(string userId, int id, CancellationToken ct = default)
    {
        var e = await _db.TradeJournalEntries.FirstOrDefaultAsync(x => x.UserId == userId && x.Id == id, ct);
        if (e is null) return;
        _db.TradeJournalEntries.Remove(e);
        await _db.SaveChangesAsync(ct);
    }
}

public sealed class NotificationPreferencesRepository : INotificationPreferencesRepository
{
    private readonly TradePersoDbContext _db;
    public NotificationPreferencesRepository(TradePersoDbContext db) => _db = db;

    public async Task<NotificationPreferences> GetOrCreateAsync(string userId, string email, CancellationToken ct = default)
    {
        var p = await _db.NotificationPreferences.FirstOrDefaultAsync(x => x.UserId == userId, ct);
        if (p is not null) return p;
        p = new NotificationPreferences { UserId = userId, Email = email };
        _db.NotificationPreferences.Add(p);
        await _db.SaveChangesAsync(ct);
        return p;
    }

    public async Task UpsertAsync(NotificationPreferences prefs, CancellationToken ct = default)
    {
        prefs.UpdatedAt = DateTimeOffset.UtcNow;
        _db.NotificationPreferences.Update(prefs);
        await _db.SaveChangesAsync(ct);
    }
}

public sealed class RecommendationRunRepository : IRecommendationRunRepository
{
    private readonly TradePersoDbContext _db;
    public RecommendationRunRepository(TradePersoDbContext db) => _db = db;

    public async Task SaveAsync(RecommendationRun run, CancellationToken ct = default)
    {
        _db.RecommendationRuns.Add(run);
        await _db.SaveChangesAsync(ct);
    }

    public Task<RecommendationRun?> GetLatestAsync(string userId, CancellationToken ct = default)
        => _db.RecommendationRuns.AsNoTracking()
            .Where(r => r.UserId == userId)
            .OrderByDescending(r => r.RunAt)
            .FirstOrDefaultAsync(ct);
}

public sealed class MonthlyPlanRepository : IMonthlyPlanRepository
{
    private readonly TradePersoDbContext _db;
    public MonthlyPlanRepository(TradePersoDbContext db) => _db = db;

    public async Task SaveAsync(MonthlyPlanEntry entry, CancellationToken ct = default)
    {
        _db.MonthlyPlans.Add(entry);
        await _db.SaveChangesAsync(ct);
    }

    public Task<MonthlyPlanEntry?> GetLatestAsync(string userId, CancellationToken ct = default)
        => _db.MonthlyPlans.AsNoTracking()
            .Where(p => p.UserId == userId)
            .OrderByDescending(p => p.CreatedAt)
            .FirstOrDefaultAsync(ct);
}
