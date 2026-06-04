using Microsoft.AspNetCore.Identity;
using TradePerso.Application.Abstractions;

namespace TradePerso.Web.Endpoints;

public static class AuthEndpoints
{
    public static IEndpointRouteBuilder MapAuthEndpoints(this IEndpointRouteBuilder app)
    {
        app.MapPost("/auth/login", async (
            HttpContext ctx,
            SignInManager<IdentityUser> signIn) =>
        {
            var form = await ctx.Request.ReadFormAsync();
            var email = form["email"].ToString();
            var password = form["password"].ToString();
            var returnUrl = form["returnUrl"].ToString();
            if (string.IsNullOrWhiteSpace(returnUrl)) returnUrl = "/";

            var result = await signIn.PasswordSignInAsync(email, password, isPersistent: true, lockoutOnFailure: false);
            if (result.Succeeded)
                return Results.Redirect(returnUrl);
            return Results.Redirect($"/login?error=1&returnUrl={Uri.EscapeDataString(returnUrl)}");
        }).DisableAntiforgery();

        app.MapPost("/auth/register", async (
            HttpContext ctx,
            UserManager<IdentityUser> users,
            SignInManager<IdentityUser> signIn,
            ISeedService seed) =>
        {
            var form = await ctx.Request.ReadFormAsync();
            var email = form["email"].ToString();
            var password = form["password"].ToString();
            if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(password))
                return Results.Redirect("/register?error=missing");

            var user = new IdentityUser { UserName = email, Email = email, EmailConfirmed = true };
            var create = await users.CreateAsync(user, password);
            if (!create.Succeeded)
            {
                var msg = string.Join("; ", create.Errors.Select(e => e.Description));
                return Results.Redirect($"/register?error={Uri.EscapeDataString(msg)}");
            }
            await seed.SeedDefaultsAsync(user.Id, email);
            await signIn.SignInAsync(user, isPersistent: true);
            return Results.Redirect("/");
        }).DisableAntiforgery();

        app.MapPost("/auth/logout", async (SignInManager<IdentityUser> signIn) =>
        {
            await signIn.SignOutAsync();
            return Results.Redirect("/login");
        }).DisableAntiforgery();

        return app;
    }
}
