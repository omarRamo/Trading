from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from config import DISCLAIMER, MANUAL_DECISION_PHRASE
from database import get_assets, load_settings, save_monthly_plan, save_recommendations
from market_data import fetch_many_market_data
from portfolio import compute_portfolio_summary
from risk_management import max_additional_amount_for_stock
from utils.formatting import round_amount


def _num(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        number = float(value)
        if pd.isna(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def _metric_direction(metric: float | None, positive_text: str, negative_text: str) -> tuple[int, str]:
    if metric is None:
        return 0, "Donnee insuffisante"
    return (1, positive_text) if metric > 0 else (-1, negative_text)


def _score_etf(asset: pd.Series, metrics: dict[str, Any], summary: dict[str, Any]) -> tuple[float, list[str]]:
    score = 45.0
    reasons: list[str] = []
    etf_gap = summary["allocation_gap"].get("ETF", 0.0)
    if etf_gap > 0:
        bonus = min(22.0, etf_gap * 100)
        score += bonus
        reasons.append(f"ETF sous-ponderes dans l'allocation cible (+{bonus:.0f})")
    else:
        score += max(-12.0, etf_gap * 50)
        reasons.append("Poche ETF deja proche ou au-dessus de la cible")

    price = _num(metrics.get("price"))
    ma200 = _num(metrics.get("ma200"))
    ma50 = _num(metrics.get("ma50"))
    perf_6m = _num(metrics.get("perf_6m"))
    perf_1m = _num(metrics.get("perf_1m"))
    volatility = _num(metrics.get("volatility"))
    rsi = _num(metrics.get("rsi14"))

    if price and ma200:
        if price > ma200:
            score += 10
            reasons.append("Prix au-dessus de la moyenne mobile 200 jours")
        else:
            score -= 10
            reasons.append("Prix sous la moyenne mobile 200 jours")
    if ma50 and ma200 and ma50 > ma200:
        score += 4
        reasons.append("MM50 au-dessus de MM200")

    direction, text = _metric_direction(perf_6m, "Tendance 6 mois positive", "Tendance 6 mois negative")
    score += 10 * direction if direction > 0 else 8 * direction
    reasons.append(text)

    if volatility is not None:
        if volatility < 0.22:
            score += 8
            reasons.append("Volatilite recente raisonnable")
        elif volatility < 0.35:
            score += 3
            reasons.append("Volatilite acceptable")
        else:
            score -= 8
            reasons.append("Volatilite elevee")
    if perf_1m is not None and perf_1m > 0.10:
        score -= 8
        reasons.append("Hausse 1 mois deja forte: prudence sur l'euphorie")
    if rsi is not None and rsi > 70:
        score -= 15
        reasons.append("RSI superieur a 70: actif potentiellement surachete")

    if metrics.get("status") == "error":
        score -= 15
        reasons.append("Donnees de marche indisponibles")
    return max(0.0, min(100.0, score)), reasons


def _score_stock(
    asset: pd.Series,
    metrics: dict[str, Any],
    summary: dict[str, Any],
    settings: dict[str, Any],
) -> tuple[float, list[str], bool]:
    score = 35.0
    reasons: list[str] = []
    blocked = False
    positions = summary.get("positions", pd.DataFrame())
    max_weight = float(settings.get("max_individual_position", 0.08))
    hard_max = float(settings.get("hard_max_individual_position", 0.10))
    if not positions.empty:
        current = positions[positions["ticker"] == asset["ticker"]]
        if not current.empty:
            weight = float(current.iloc[0].get("weight", 0))
            if weight >= hard_max:
                blocked = True
                return 0.0, [f"Position deja au-dessus de la limite dure {hard_max:.0%}"], blocked
            if weight >= max_weight:
                score -= 25
                reasons.append(f"Position deja proche de la limite personnelle {max_weight:.0%}")

    price = _num(metrics.get("price"))
    ma200 = _num(metrics.get("ma200"))
    ma50 = _num(metrics.get("ma50"))
    perf_6m = _num(metrics.get("perf_6m"))
    perf_1m = _num(metrics.get("perf_1m"))
    volatility = _num(metrics.get("volatility"))
    rsi = _num(metrics.get("rsi14"))

    if price and ma200:
        if price > ma200:
            score += 12
            reasons.append("Prix au-dessus de MM200")
        else:
            score -= 10
            reasons.append("Prix sous MM200")
    if ma50 and ma200:
        if ma50 > ma200:
            score += 10
            reasons.append("MM50 au-dessus de MM200")
        else:
            score -= 4
            reasons.append("MM50 sous MM200")
    direction, text = _metric_direction(perf_6m, "Tendance long terme positive", "Tendance 6 mois negative")
    score += 10 * direction if direction > 0 else 6 * direction
    reasons.append(text)

    if rsi is not None and rsi > 70:
        score -= 15
        reasons.append("RSI superieur a 70: achat bloque ou a temporiser")
    if volatility is not None:
        if volatility > 0.50:
            score -= 16
            reasons.append("Volatilite tres elevee")
        elif volatility > 0.35:
            score -= 7
            reasons.append("Volatilite elevee")
        else:
            score += 5
            reasons.append("Volatilite contenue")
    if perf_1m is not None and perf_1m < -0.15 and price and ma50 and price < ma50:
        score -= 12
        reasons.append("Baisse recente forte sans stabilisation technique")
    if metrics.get("status") == "error":
        score -= 15
        reasons.append("Donnees de marche indisponibles")
    return max(0.0, min(100.0, score)), reasons, blocked


def prudence_level(score: float, blocked: bool = False) -> str:
    if blocked or score < 35:
        return "éviter"
    if score >= 75:
        return "intéressant"
    if score >= 55:
        return "à surveiller"
    return "attendre"


def _risk_level(
    asset_type: str,
    ticker: str,
    metrics: dict[str, Any],
    summary: dict[str, Any],
    settings: dict[str, Any],
) -> str:
    if metrics.get("status") == "error":
        return "inconnu"

    points = 1 if asset_type == "ACTION" else 0
    volatility = _num(metrics.get("volatility"))
    rsi = _num(metrics.get("rsi14"))

    if volatility is not None:
        if volatility > 0.50:
            points += 3
        elif volatility > 0.35:
            points += 2
        elif volatility > 0.22:
            points += 1

    if rsi is not None and rsi > 70:
        points += 1

    positions = summary.get("positions", pd.DataFrame())
    if asset_type == "ACTION" and not positions.empty:
        current = positions[positions["ticker"] == ticker]
        if not current.empty:
            weight = float(current.iloc[0].get("weight", 0))
            max_weight = float(settings.get("max_individual_position", 0.08))
            hard_max = float(settings.get("hard_max_individual_position", 0.10))
            if weight >= hard_max:
                points += 3
            elif weight >= max_weight:
                points += 2

    if points >= 5:
        return "très élevé"
    if points >= 3:
        return "élevé"
    if points >= 1:
        return "modéré"
    return "faible"


def _idea_reason(reasons: list[str], score: float) -> str:
    positive_markers = [
        "sous-ponder",
        "au-dessus",
        "positive",
        "raisonnable",
        "acceptable",
        "contenue",
    ]
    positives = [
        reason
        for reason in reasons
        if any(marker in reason.lower() for marker in positive_markers)
    ]
    if positives:
        return " ; ".join(positives[:3])
    return f"Score de qualite {score:.1f}/100 selon les regles d'allocation, de tendance et de risque."


def _vigilance_points(
    asset: pd.Series,
    metrics: dict[str, Any],
    summary: dict[str, Any],
    settings: dict[str, Any],
    blocked: bool,
) -> list[str]:
    points: list[str] = []
    if blocked:
        points.append("Plafond de concentration deja atteint ou depasse.")
    if metrics.get("status") in {"error", "stale"}:
        points.append("Donnees de marche indisponibles ou issues du cache.")

    rsi = _num(metrics.get("rsi14"))
    volatility = _num(metrics.get("volatility"))
    perf_1m = _num(metrics.get("perf_1m"))
    perf_6m = _num(metrics.get("perf_6m"))
    price = _num(metrics.get("price"))
    ma200 = _num(metrics.get("ma200"))

    if rsi is not None and rsi > 70:
        points.append("RSI superieur a 70: risque de surachat.")
    if volatility is not None and volatility > 0.35:
        points.append("Volatilite recente elevee.")
    if perf_1m is not None and perf_1m > 0.10:
        points.append("Hausse recente forte: eviter l'achat impulsif.")
    if perf_1m is not None and perf_1m < -0.15:
        points.append("Baisse recente forte: verifier la stabilisation.")
    if perf_6m is not None and perf_6m < 0:
        points.append("Tendance 6 mois negative.")
    if price and ma200 and price < ma200:
        points.append("Prix sous la moyenne mobile 200 jours.")

    positions = summary.get("positions", pd.DataFrame())
    if asset["asset_type"] == "ACTION" and not positions.empty:
        current = positions[positions["ticker"] == asset["ticker"]]
        if not current.empty:
            weight = float(current.iloc[0].get("weight", 0))
            max_weight = float(settings.get("max_individual_position", 0.08))
            if weight >= max_weight * 0.8:
                points.append("Position deja significative dans le portefeuille.")

    if not points:
        points.append("Aucun point de vigilance majeur dans les regles du MVP.")
    return points[:5]


def _max_theoretical_amount(
    asset_type: str,
    ticker: str,
    summary: dict[str, Any],
    settings: dict[str, Any],
    monthly_amount: float,
) -> float:
    bucket_amounts = _adjust_bucket_amounts(monthly_amount, summary)
    if asset_type == "ETF":
        return max(0.0, float(bucket_amounts["ETF"]))
    stock_budget = max(0.0, float(bucket_amounts["ACTION"]))
    concentration_cap = max_additional_amount_for_stock(ticker, summary, settings, monthly_amount)
    return round_amount(min(stock_budget, concentration_cap))


def generate_recommendations(force_market_refresh: bool = False, persist: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    settings = load_settings()
    assets = get_assets(active_only=True)
    if assets.empty:
        return [], compute_portfolio_summary(settings)

    market_data = fetch_many_market_data(assets["ticker"].tolist(), force_refresh=force_market_refresh)
    summary = compute_portfolio_summary(settings, market_data=market_data)
    recommendations: list[dict[str, Any]] = []
    monthly_amount = float(settings.get("monthly_investment", 1000))

    for _, asset in assets.iterrows():
        metrics = market_data.get(asset["ticker"], {})
        if asset["asset_type"] == "ETF":
            score, reasons = _score_etf(asset, metrics, summary)
            blocked = False
        else:
            score, reasons, blocked = _score_stock(asset, metrics, summary, settings)
        recommendations.append(
            {
                "ticker": asset["ticker"],
                "name": asset["name"],
                "asset_type": asset["asset_type"],
                "score": round(score, 1),
                "recommended_amount": 0.0,
                "max_theoretical_amount": _max_theoretical_amount(
                    asset["asset_type"], asset["ticker"], summary, settings, monthly_amount
                ),
                "prudence_level": prudence_level(score, blocked),
                "risk_level": _risk_level(asset["asset_type"], asset["ticker"], metrics, summary, settings),
                "idea_reason": _idea_reason(reasons, score),
                "vigilance_points": _vigilance_points(asset, metrics, summary, settings, blocked),
                "reasons": reasons[:5],
                "metrics": {
                    "price": metrics.get("price"),
                    "perf_1m": metrics.get("perf_1m"),
                    "perf_6m": metrics.get("perf_6m"),
                    "rsi14": metrics.get("rsi14"),
                    "volatility": metrics.get("volatility"),
                    "status": metrics.get("status"),
                },
                "disclaimer": DISCLAIMER,
                "manual_decision": MANUAL_DECISION_PHRASE,
            }
        )

    recommendations = sorted(recommendations, key=lambda item: item["score"], reverse=True)
    if persist:
        save_recommendations(recommendations)
    return recommendations, summary


def _adjust_bucket_amounts(monthly_amount: float, summary: dict[str, Any]) -> dict[str, float]:
    target = summary["allocation_target"]
    current = summary["allocation_current"]
    scores = {}
    for bucket in ["ETF", "ACTION", "CASH"]:
        gap = target[bucket] - current.get(bucket, 0.0)
        score = target[bucket] + max(0.0, gap) * 1.8 + min(0.0, gap) * 1.1
        scores[bucket] = max(0.0, score)

    if current.get("CASH", 0.0) < target["CASH"] - 0.02:
        scores["CASH"] += 0.20
    if current.get("ACTION", 0.0) > target["ACTION"] + 0.03:
        scores["ACTION"] = 0.0
    if current.get("ETF", 0.0) > target["ETF"] + 0.05:
        scores["ETF"] *= 0.35

    total_score = sum(scores.values()) or 1.0
    amounts = {bucket: round_amount(monthly_amount * score / total_score) for bucket, score in scores.items()}
    delta = round(monthly_amount - sum(amounts.values()), 2)
    amounts["CASH"] = round(amounts["CASH"] + delta, 2)
    return amounts


def _allocate_to_candidates(
    candidates: list[dict[str, Any]],
    budget: float,
    asset_type: str,
    summary: dict[str, Any],
    settings: dict[str, Any],
    monthly_amount: float,
) -> tuple[list[dict[str, Any]], float, list[str]]:
    warnings: list[str] = []
    if budget <= 0:
        return candidates, 0.0, warnings

    if asset_type == "ETF":
        eligible = [c for c in candidates if c["asset_type"] == "ETF" and c["prudence_level"] != "éviter"][:5]
    else:
        eligible = [c for c in candidates if c["asset_type"] == "ACTION" and c["score"] >= 55 and c["prudence_level"] != "éviter"][:5]
    if not eligible:
        warnings.append(f"Aucun candidat {asset_type} n'a passe les filtres de prudence.")
        return candidates, 0.0, warnings

    total_score = sum(max(1.0, c["score"]) for c in eligible)
    used = 0.0
    for candidate in eligible:
        raw_amount = budget * max(1.0, candidate["score"]) / total_score
        amount = round_amount(raw_amount)
        if asset_type == "ACTION":
            cap = max_additional_amount_for_stock(candidate["ticker"], summary, settings, monthly_amount)
            if cap <= 0:
                amount = 0.0
                candidate["prudence_level"] = "éviter"
                candidate["reasons"] = ["Achat bloque par la limite de concentration"] + candidate["reasons"]
                candidate["vigilance_points"] = ["Plafond de concentration atteint."] + candidate.get("vigilance_points", [])
            elif amount > cap:
                amount = round_amount(cap)
                warnings.append(f"{candidate['ticker']} plafonne par la limite de concentration.")
        candidate["recommended_amount"] = max(0.0, amount)
        used += candidate["recommended_amount"]
    return candidates, used, warnings


def build_monthly_plan(
    monthly_amount: float | None = None,
    recommendations: list[dict[str, Any]] | None = None,
    summary: dict[str, Any] | None = None,
    settings: dict[str, Any] | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    if settings is None:
        settings = load_settings()
    if recommendations is None or summary is None:
        recommendations, summary = generate_recommendations()
    monthly_amount = float(monthly_amount if monthly_amount is not None else settings.get("monthly_investment", 1000))
    bucket_amounts = _adjust_bucket_amounts(monthly_amount, summary)

    recommendations = [dict(rec) for rec in recommendations]
    for candidate in recommendations:
        candidate["max_theoretical_amount"] = _max_theoretical_amount(
            candidate["asset_type"], candidate["ticker"], summary, settings, monthly_amount
        )
    recommendations, used_etf, etf_warnings = _allocate_to_candidates(
        recommendations, bucket_amounts["ETF"], "ETF", summary, settings, monthly_amount
    )
    recommendations, used_stocks, stock_warnings = _allocate_to_candidates(
        recommendations, bucket_amounts["ACTION"], "ACTION", summary, settings, monthly_amount
    )

    unused = max(0.0, bucket_amounts["ETF"] - used_etf) + max(0.0, bucket_amounts["ACTION"] - used_stocks)
    bucket_amounts["CASH"] = round(bucket_amounts["CASH"] + unused, 2)
    bucket_amounts["ETF"] = round(used_etf, 2)
    bucket_amounts["ACTION"] = round(used_stocks, 2)

    items = [
        {
            "ticker": rec["ticker"],
            "name": rec["name"],
            "asset_type": rec["asset_type"],
            "score": rec["score"],
            "recommended_amount": rec["recommended_amount"],
            "max_theoretical_amount": rec.get("max_theoretical_amount", 0.0),
            "prudence_level": rec["prudence_level"],
            "risk_level": rec.get("risk_level", "inconnu"),
            "idea_reason": rec.get("idea_reason", ""),
            "vigilance_points": rec.get("vigilance_points", []),
            "reasons": rec["reasons"],
            "manual_decision": rec.get("manual_decision", MANUAL_DECISION_PHRASE),
        }
        for rec in recommendations
        if rec["recommended_amount"] > 0
    ]
    watch_items = [
        rec for rec in recommendations if rec["recommended_amount"] == 0 and rec["prudence_level"] in {"à surveiller", "attendre"}
    ][:8]
    warnings = etf_warnings + stock_warnings
    if bucket_amounts["CASH"] > monthly_amount * 0.25:
        warnings.append("Part cash elevee ce mois-ci: le moteur privilegie la prudence ou reconstitue la poche opportunites.")

    plan = {
        "plan_date": datetime.now().strftime("%Y-%m-%d"),
        "monthly_amount": monthly_amount,
        "bucket_amounts": bucket_amounts,
        "items": items,
        "watch_items": watch_items,
        "warnings": warnings,
        "disclaimer": DISCLAIMER,
    }
    if persist:
        save_monthly_plan(plan)
        save_recommendations(recommendations)
    return plan
