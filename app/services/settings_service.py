from __future__ import annotations

from ..database import Database


class SettingsService:
    DEFAULT_BLOCK_DAYS = 15
    MIN_BLOCK_DAYS = 0
    MAX_BLOCK_DAYS = 90
    KEY_BLOCK_DAYS = "dias_bloqueo_venta_vencimiento"

    DEFAULT_THEME = "dark"
    VALID_THEMES = {"dark", "light"}
    KEY_THEME = "tema_apariencia"

    DEFAULT_INACTIVITY_MINUTES = 0
    MIN_INACTIVITY_MINUTES = 0
    MAX_INACTIVITY_MINUTES = 240
    KEY_INACTIVITY = "minutos_bloqueo_inactividad"

    def __init__(self, db: Database) -> None:
        self.db = db

    def _get(self, key: str, default: str) -> str:
        with self.db.connect() as con:
            row = con.execute("SELECT valor FROM configuracion WHERE clave=?", (key,)).fetchone()
        return str(row["valor"]).strip() if row else default

    def _set(self, key: str, value: str) -> None:
        with self.db.transaction() as con:
            con.execute(
                """
                INSERT INTO configuracion(clave, valor, actualizado_en)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(clave) DO UPDATE SET
                    valor=excluded.valor,
                    actualizado_en=CURRENT_TIMESTAMP
                """,
                (key, value),
            )

    def get_block_days(self) -> int:
        raw = self._get(self.KEY_BLOCK_DAYS, str(self.DEFAULT_BLOCK_DAYS))
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return self.DEFAULT_BLOCK_DAYS
        return max(self.MIN_BLOCK_DAYS, min(self.MAX_BLOCK_DAYS, value))

    def set_block_days(self, days: int) -> int:
        try:
            days = int(days)
        except (TypeError, ValueError) as exc:
            raise ValueError("Los días de bloqueo deben ser un número entero.") from exc
        if not self.MIN_BLOCK_DAYS <= days <= self.MAX_BLOCK_DAYS:
            raise ValueError(
                f"Los días de bloqueo deben estar entre {self.MIN_BLOCK_DAYS} y {self.MAX_BLOCK_DAYS}."
            )
        self._set(self.KEY_BLOCK_DAYS, str(days))
        return days

    def get_theme(self) -> str:
        value = self._get(self.KEY_THEME, self.DEFAULT_THEME).lower()
        return value if value in self.VALID_THEMES else self.DEFAULT_THEME

    def set_theme(self, theme: str) -> str:
        theme = str(theme).strip().lower()
        if theme not in self.VALID_THEMES:
            raise ValueError("El tema debe ser oscuro o claro.")
        self._set(self.KEY_THEME, theme)
        return theme

    def get_inactivity_minutes(self) -> int:
        raw = self._get(self.KEY_INACTIVITY, str(self.DEFAULT_INACTIVITY_MINUTES))
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return self.DEFAULT_INACTIVITY_MINUTES
        return max(self.MIN_INACTIVITY_MINUTES, min(self.MAX_INACTIVITY_MINUTES, value))

    def set_inactivity_minutes(self, minutes: int) -> int:
        try:
            minutes = int(minutes)
        except (TypeError, ValueError) as exc:
            raise ValueError("El tiempo de inactividad debe ser un número entero.") from exc
        if not self.MIN_INACTIVITY_MINUTES <= minutes <= self.MAX_INACTIVITY_MINUTES:
            raise ValueError(
                f"El tiempo de inactividad debe estar entre {self.MIN_INACTIVITY_MINUTES} y {self.MAX_INACTIVITY_MINUTES} minutos."
            )
        self._set(self.KEY_INACTIVITY, str(minutes))
        return minutes
