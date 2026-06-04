using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using TradePerso.Application.Abstractions;
using TradePerso.Application.Abstractions.Repositories;
using TradePerso.Application.DTOs;
using TradePerso.Domain.Entities;
using TradePerso.Web.Services;

namespace TradePerso.Web.Endpoints;

public static class ApiEndpoints
{
    public static IEndpointRouteBuilder MapTradePersoApi(this IEndpointRouteBuilder app)
    {
        var api = app.MapGroup("/api").RequireAuthorization();

        api.MapGet("/portfolio", async Task<IResult> (IPortfolioService svc, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                return Results.Ok(await svc.ComputeSummaryAsync(uid));
            })
            .WithName("GetPortfolio").WithSummary("Get the current user's portfolio summary")
            .WithTags("Portfolio").Produces<PortfolioSummaryDto>();

        api.MapGet("/recommendations", async Task<IResult> (IRecommendationService svc, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                return Results.Ok(await svc.GenerateAsync(uid));
            })
            .WithName("GetRecommendations").WithSummary("Generate ranked investment ideas")
            .WithTags("Recommendations").Produces<IReadOnlyList<RecommendationDto>>();

        api.MapGet("/monthly-plan", async Task<IResult> (IMonthlyPlanService svc, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                return Results.Ok(await svc.BuildAsync(uid));
            })
            .WithName("GetMonthlyPlan").WithSummary("Build the monthly DCA plan")
            .WithTags("MonthlyPlan").Produces<MonthlyPlanResultDto>();

        api.MapGet("/risk-alerts", async Task<IResult> (IRiskService svc, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                return Results.Ok(await svc.EvaluateAsync(uid));
            })
            .WithName("GetRiskAlerts").WithSummary("Evaluate risk alerts on the current portfolio")
            .WithTags("Risk").Produces<IReadOnlyList<RiskAlertDto>>();

        api.MapPost("/market-sync", async Task<IResult> (IMarketSyncService svc, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                var n = await svc.SyncAsync(uid);
                return Results.Ok(new { synced = n });
            })
            .WithName("RunMarketSync").WithSummary("Trigger a market data sync for active tickers")
            .WithTags("Markets");

        api.MapGet("/positions", async Task<IResult> (IPositionRepository repo, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                return Results.Ok(await repo.ListAsync(uid));
            })
            .WithName("GetPositions").WithTags("Portfolio").Produces<IReadOnlyList<Position>>();

        api.MapPost("/positions", async Task<IResult> (Position position, IPositionRepository repo, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                position.UserId = uid;
                await repo.UpsertAsync(position);
                return Results.Ok(position);
            })
            .WithName("UpsertPosition").WithTags("Portfolio");

        api.MapDelete("/positions/{ticker}", async Task<IResult> (string ticker, IPositionRepository repo, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                await repo.DeleteAsync(uid, ticker);
                return Results.NoContent();
            })
            .WithName("DeletePosition").WithTags("Portfolio");

        api.MapGet("/transactions", async Task<IResult> (ITransactionRepository repo, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                return Results.Ok(await repo.ListAsync(uid));
            })
            .WithName("GetTransactions").WithTags("Transactions");

        api.MapPost("/transactions", async Task<IResult> (Transaction tx, ITransactionRepository repo, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                tx.UserId = uid;
                await repo.AddAsync(tx);
                return Results.Created($"/api/transactions/{tx.Id}", tx);
            })
            .WithName("AddTransaction").WithTags("Transactions");

        api.MapPost("/backtest", async Task<IResult> (
                [FromQuery] string ticker,
                [FromQuery] DateOnly startDate,
                [FromQuery] DateOnly endDate,
                [FromQuery] decimal monthlyAmount,
                [FromQuery] decimal initialCash,
                IBacktestService svc) =>
            {
                var result = await svc.RunAsync(ticker, startDate, endDate, monthlyAmount, initialCash);
                return Results.Ok(result);
            })
            .WithName("RunBacktest").WithTags("Backtest").Produces<BacktestResultDto>();

        api.MapGet("/settings", async Task<IResult> (IUserSettingsRepository repo, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                return Results.Ok(await repo.GetOrCreateAsync(uid));
            })
            .WithName("GetSettings").WithTags("Settings").Produces<UserSettings>();

        api.MapPut("/settings", async Task<IResult> (UserSettings settings, IUserSettingsRepository repo, CurrentUserAccessor user) =>
            {
                var uid = await user.GetUserIdAsync();
                if (uid is null) return Results.Unauthorized();
                settings.UserId = uid;
                await repo.UpdateAsync(settings);
                return Results.Ok(settings);
            })
            .WithName("UpdateSettings").WithTags("Settings");

        return app;
    }
}
