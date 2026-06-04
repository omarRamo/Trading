using Microsoft.AspNetCore.Components.Authorization;

namespace TradePerso.Web.Services;

public sealed class CurrentUserAccessor
{
    private readonly AuthenticationStateProvider _provider;
    public CurrentUserAccessor(AuthenticationStateProvider provider) => _provider = provider;

    public async Task<string?> GetUserIdAsync()
    {
        var state = await _provider.GetAuthenticationStateAsync();
        return state.User?.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
    }

    public async Task<string?> GetEmailAsync()
    {
        var state = await _provider.GetAuthenticationStateAsync();
        return state.User?.Identity?.Name;
    }
}
