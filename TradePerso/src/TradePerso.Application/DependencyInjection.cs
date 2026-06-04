using Microsoft.Extensions.DependencyInjection;
using TradePerso.Application.Abstractions;
using TradePerso.Application.Services;

namespace TradePerso.Application;

public static class DependencyInjection
{
    public static IServiceCollection AddTradePersoApplication(this IServiceCollection services)
    {
        services.AddScoped<IPortfolioService, PortfolioService>();
        services.AddScoped<IRecommendationService, RecommendationService>();
        services.AddScoped<IMonthlyPlanService, MonthlyPlanService>();
        services.AddScoped<IBacktestService, BacktestService>();
        services.AddScoped<IRiskService, RiskService>();
        services.AddScoped<IPositionSizingService, PositionSizingService>();
        services.AddScoped<IMarketSyncService, MarketSyncService>();
        services.AddScoped<ISeedService, SeedService>();
        return services;
    }
}
