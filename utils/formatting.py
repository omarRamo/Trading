def format_currency(value: float | int | None, currency: str = "EUR") -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):,.2f} {currency}".replace(",", " ")
    except (TypeError, ValueError):
        return "-"


def format_percent(value: float | int | None) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.2f} %"
    except (TypeError, ValueError):
        return "-"


def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def round_amount(value: float, step: float = 5.0) -> float:
    if step <= 0:
        return round(value, 2)
    return round(round(value / step) * step, 2)
