from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "FarmaStock"
APP_DESCRIPTOR = "Sistema de Inventario de Medicamentos"
APP_SLUG = "FarmaStock"
VERSION = "1.0.0"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSET_DIR / "farmastock_logo.png"


def _default_data_dir() -> Path:
    custom = os.getenv("SIM_DATA_DIR") or os.getenv("FARMASTOCK_DATA_DIR")
    if custom:
        return Path(custom).expanduser().resolve()

    if sys.platform.startswith("win"):
        base = Path(os.getenv("LOCALAPPDATA") or Path.home())
        return base / APP_SLUG

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_SLUG

    return Path.home() / ".local" / "share" / APP_SLUG


DATA_DIR = _default_data_dir()
DB_PATH = DATA_DIR / "farmastock.db"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"


def ensure_directories() -> None:
    for path in (DATA_DIR, BACKUP_DIR, EXPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)
