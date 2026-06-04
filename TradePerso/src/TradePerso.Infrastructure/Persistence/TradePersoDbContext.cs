using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;
using TradePerso.Domain.Entities;

namespace TradePerso.Infrastructure.Persistence;

public class TradePersoDbContext : IdentityDbContext<IdentityUser>
{
    public TradePersoDbContext(DbContextOptions<TradePersoDbContext> options) : base(options) { }

    public DbSet<UserSettings> UserSettings => Set<UserSettings>();
    public DbSet<Asset> Assets => Set<Asset>();
    public DbSet<Position> Positions => Set<Position>();
    public DbSet<Transaction> Transactions => Set<Transaction>();
    public DbSet<RecommendationRun> RecommendationRuns => Set<RecommendationRun>();
    public DbSet<MonthlyPlanEntry> MonthlyPlans => Set<MonthlyPlanEntry>();
    public DbSet<TradeJournalEntry> TradeJournalEntries => Set<TradeJournalEntry>();
    public DbSet<NotificationPreferences> NotificationPreferences => Set<NotificationPreferences>();
    public DbSet<PriceAlert> PriceAlerts => Set<PriceAlert>();

    protected override void OnModelCreating(ModelBuilder b)
    {
        base.OnModelCreating(b);
        b.Entity<UserSettings>().HasIndex(x => x.UserId).IsUnique();
        b.Entity<Asset>().HasIndex(x => new { x.UserId, x.Ticker }).IsUnique();
        b.Entity<Position>().HasIndex(x => new { x.UserId, x.Ticker }).IsUnique();
        b.Entity<NotificationPreferences>().HasIndex(x => x.UserId).IsUnique();

        foreach (var et in b.Model.GetEntityTypes())
        {
            foreach (var prop in et.GetProperties()
                .Where(p => p.ClrType == typeof(decimal) || p.ClrType == typeof(decimal?)))
            {
                prop.SetColumnType("decimal(18,6)");
            }
        }
    }
}
