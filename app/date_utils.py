from __future__ import annotations

from datetime import datetime, timezone


def display_date(value: str | None) -> str:
    if not value:
        return "Sin fecha"
    try:
        dt = datetime.fromisoformat(value[:10])
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return value


def display_datetime(value: str | None) -> str:
    if not value:
        return ""
    try:
        raw = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if raw.tzinfo is None:
            raw = raw.replace(tzinfo=timezone.utc)
        local = raw.astimezone()
        return local.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return value


def display_bytes(size: int | float) -> str:
    size = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
