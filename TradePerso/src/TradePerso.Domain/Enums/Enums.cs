namespace TradePerso.Domain.Enums;

public enum AssetType
{
    Etf = 0,
    Stock = 1,
    Cash = 2,
}

public enum TransactionType
{
    Buy = 0,
    Sell = 1,
}

public enum PrudenceLevel
{
    Interesting = 0,
    Watch = 1,
    Wait = 2,
    Avoid = 3,
}

public enum RiskProfile
{
    Conservative = 0,
    Balanced = 1,
    Dynamic = 2,
}

public enum TradeDirection
{
    Long = 0,
    Short = 1,
}

public enum TradeStatus
{
    Open = 0,
    Closed = 1,
}

public enum AppLanguage
{
    English = 0,
    French = 1,
}
