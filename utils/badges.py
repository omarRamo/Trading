from __future__ import annotations


def signal_badge(level: str) -> str:
    normalized = (level or '').strip().lower()
    mapping = {
        'intéressant': '🟢 intéressant',
        'interessant': '🟢 intéressant',
        'à surveiller': '🟡 à surveiller',
        'a surveiller': '🟡 à surveiller',
        'attendre': '⚪ attendre',
        'éviter': '🔴 éviter',
        'eviter': '🔴 éviter',
    }
    return mapping.get(normalized, f'⚪ {level or "inconnu"}')
