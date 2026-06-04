using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Domain.Contracts;
using TradePerso.Infrastructure.MarketData;
using TradePerso.Infrastructure.Persistence;
using TradePerso.Infrastructure.Repositories;

namespace TradePerso.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddTradePersoInfrastructure(
        this IServiceCollection services, IConfiguration configuration)
    {
        var connectionString = configuration.GetConnectionString("TradePerso")
            ?? "Data Source=tradeperso.db";

        services.AddDbContext<TradePersoDbContext>(opt => opt.UseSqlite(connectionString));

        services.AddScoped<IUserSettingsRepository, UserSettingsRepository>();
        services.AddScoped<IAssetRepository, AssetRepository>();
        services.AddScoped<IPositionRepository, PositionRepository>();
        services.AddScoped<ITransactionRepository, TransactionRepository>();
        services.AddScoped<ITradeJournalRepository, TradeJournalRepository>();
        services.AddScoped<INotificationPreferencesRepository, NotificationPreferencesRepository>();
        services.AddScoped<IRecommendationRunRepository, RecommendationRunRepository>();
        services.AddScoped<IMonthlyPlanRepository, MonthlyPlanRepository>();

        services.AddMemoryCache();
        services.Configure<MarketDataOptions>(configuration.GetSection(MarketDataOptions.SectionName));

        var providerName = configuration.GetSection(MarketDataOptions.SectionName)["Provider"] ?? "Yahoo";
        if (providerName.Equals("Sample", StringComparison.OrdinalIgnoreCase))
        {
            services.AddSingleton<IMarketDataProvider, SampleMarketDataProvider>();
        }
        else
        {
            services.AddHttpClient<IMarketDataProvider, YahooFinanceMarketDataProvider>(client =>
            {
                client.Timeout = TimeSpan.FromSeconds(15);
            });
        }

        return services;
    }
}
