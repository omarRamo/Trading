using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.OpenApi.Models;
using MudBlazor.Services;
using TradePerso.Application;
using TradePerso.Application.Abstractions;
using TradePerso.Infrastructure;
using TradePerso.Infrastructure.Persistence;
using TradePerso.Web.Components;
using TradePerso.Web.Endpoints;
using TradePerso.Web.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

builder.Services.AddTradePersoInfrastructure(builder.Configuration);
builder.Services.AddTradePersoApplication();
builder.Services.AddMudServices();
builder.Services.AddHttpContextAccessor();

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "TradePerso API",
        Version = "v1",
        Description = "REST API for the TradePerso trading companion (portfolio, recommendations, backtest, settings)."
    });
});

builder.Services
    .AddIdentity<IdentityUser, IdentityRole>(options =>
    {
        options.SignIn.RequireConfirmedAccount = false;
        options.Password.RequireDigit = false;
        options.Password.RequireUppercase = false;
        options.Password.RequireNonAlphanumeric = false;
        options.Password.RequiredLength = 4;
        options.User.RequireUniqueEmail = true;
    })
    .AddEntityFrameworkStores<TradePersoDbContext>()
    .AddDefaultTokenProviders();

builder.Services.ConfigureApplicationCookie(opt =>
{
    opt.LoginPath = "/login";
    opt.LogoutPath = "/auth/logout";
    opt.AccessDeniedPath = "/login";
    opt.ExpireTimeSpan = TimeSpan.FromDays(14);
    opt.SlidingExpiration = true;
});

builder.Services.AddCascadingAuthenticationState();
builder.Services.AddAuthorization();
builder.Services.AddScoped<CurrentUserAccessor>();

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseAntiforgery();
app.UseAuthentication();
app.UseAuthorization();

app.UseSwagger();
app.UseSwaggerUI(options =>
{
    options.SwaggerEndpoint("/swagger/v1/swagger.json", "TradePerso API v1");
    options.RoutePrefix = "swagger";
    options.DocumentTitle = "TradePerso API";
});

app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.MapAuthEndpoints();
app.MapTradePersoApi();

// Apply migrations / ensure created and seed demo user.
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<TradePersoDbContext>();
    await db.Database.EnsureCreatedAsync();
    var userMgr = scope.ServiceProvider.GetRequiredService<UserManager<IdentityUser>>();
    var demoEmail = builder.Configuration["Demo:Email"] ?? "omar@tradeperso.local";
    var demoPass = builder.Configuration["Demo:Password"] ?? "admin";
    if (await userMgr.FindByEmailAsync(demoEmail) is null)
    {
        var user = new IdentityUser { UserName = demoEmail, Email = demoEmail, EmailConfirmed = true };
        await userMgr.CreateAsync(user, demoPass);
        var seed = scope.ServiceProvider.GetRequiredService<ISeedService>();
        await seed.SeedDefaultsAsync(user.Id, demoEmail);
    }
}

app.Run();
