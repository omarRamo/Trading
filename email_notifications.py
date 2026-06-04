from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any


@dataclass
class EmailResult:
    ok: bool
    message: str
    subject: str
    item_count: int


def _smtp_config() -> dict[str, Any]:
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_SENDER", username).strip()
    use_tls = str(os.getenv("SMTP_USE_TLS", "1")).strip() not in {"0", "false", "False"}
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
        "use_tls": use_tls,
    }


def _filter_recommendations(recommendations: list[dict[str, Any]], preferences: dict[str, Any]) -> list[dict[str, Any]]:
    min_score = float(preferences.get("min_score", 60.0))
    asset_types = set(preferences.get("asset_types", ["ETF", "ACTION"]))
    max_items = int(preferences.get("max_items", 10))

    filtered = [
        rec
        for rec in recommendations
        if float(rec.get("score", 0.0)) >= min_score and rec.get("asset_type") in asset_types
    ]
    filtered.sort(key=lambda item: float(item.get("score", 0.0)), reverse=True)
    return filtered[: max(1, max_items)]


def _build_subject(item_count: int) -> str:
    date_label = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"Trading Digest - {item_count} recommendation(s) - {date_label}"


def _build_text_body(ideas: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        "Investment recommendations digest",
        "",
        f"Portfolio total value: {summary.get('total_value', 0):,.2f} {summary.get('currency', 'EUR')}",
        "",
        "Top candidates:",
    ]
    for idea in ideas:
        lines.append(
            "- "
            + f"{idea.get('ticker')} | {idea.get('asset_type')} | "
            + f"score {idea.get('score')} | signal {idea.get('prudence_level')} | "
            + f"max amount {idea.get('max_theoretical_amount', 0):,.2f}"
        )
    lines.append("")
    lines.append("Manual validation required before any order.")
    return "\n".join(lines)


def _build_html_body(ideas: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    rows = []
    for idea in ideas:
        rows.append(
            "<tr>"
            + f"<td>{idea.get('ticker')}</td>"
            + f"<td>{idea.get('asset_type')}</td>"
            + f"<td>{idea.get('score')}</td>"
            + f"<td>{idea.get('prudence_level')}</td>"
            + f"<td>{idea.get('risk_level', 'unknown')}</td>"
            + f"<td>{idea.get('max_theoretical_amount', 0):,.2f}</td>"
            + "</tr>"
        )
    rows_html = "".join(rows)
    return f"""
    <html>
      <body style=\"font-family:Segoe UI,Arial,sans-serif;\">
        <h2>Investment recommendations digest</h2>
        <p><strong>Portfolio total value:</strong> {summary.get('total_value', 0):,.2f} {summary.get('currency', 'EUR')}</p>
        <table border=\"1\" cellspacing=\"0\" cellpadding=\"6\" style=\"border-collapse:collapse;\">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Type</th>
              <th>Score</th>
              <th>Signal</th>
              <th>Risk</th>
              <th>Max Amount</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
        <p style=\"margin-top:14px;\">Manual validation required before any order.</p>
      </body>
    </html>
    """


def send_recommendations_digest(
    recommendations: list[dict[str, Any]],
    summary: dict[str, Any],
    preferences: dict[str, Any],
    target_email: str | None = None,
) -> EmailResult:
    selected = _filter_recommendations(recommendations, preferences)
    if not selected:
        return EmailResult(False, "No recommendation matched your notification filters.", "", 0)

    cfg = _smtp_config()
    if not cfg["host"] or not cfg["sender"]:
        return EmailResult(
            False,
            "SMTP config missing. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD and SMTP_SENDER.",
            "",
            0,
        )

    recipient = (target_email or preferences.get("email") or "").strip()
    if not recipient:
        return EmailResult(False, "Missing destination email in notification settings.", "", 0)

    subject = _build_subject(len(selected))
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["sender"]
    msg["To"] = recipient
    msg.set_content(_build_text_body(selected, summary))
    msg.add_alternative(_build_html_body(selected, summary), subtype="html")

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=25) as smtp:
            if cfg["use_tls"]:
                smtp.starttls()
            if cfg["username"]:
                smtp.login(cfg["username"], cfg["password"])
            smtp.send_message(msg)
        return EmailResult(True, f"Digest sent to {recipient}", subject, len(selected))
    except Exception as exc:
        return EmailResult(False, f"SMTP send failed: {exc}", subject, len(selected))
