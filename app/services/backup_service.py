from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from ..config import BACKUP_DIR, DB_PATH
from ..database import Database


class BackupService:
    """Copia y restauración de la base con una estrategia simple de dos capas.

    - ``backup_inicio_YYYYMMDD.db``: snapshot inmutable al inicio del día. Se
      conservan los últimos 7 días.
    - ``backup_ultimo_cierre.db``: copia más reciente al cerrar normalmente. Se
      reemplaza para evitar acumular archivos por cada apertura/cierre.
    - Los respaldos manuales y previos a restauración nunca participan en la
      rotación automática.
    """

    AUTO_RETENTION_DAYS = 7

    def __init__(self, db: Database) -> None:
        self.db = db
        self.backup_dir = BACKUP_DIR if Path(db.path).resolve() == Path(DB_PATH).resolve() else Path(db.path).parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate_backup_schema(con: sqlite3.Connection) -> None:
        required_tables = {
            "usuarios", "productos", "entradas", "lotes", "ventas",
            "detalle_ventas", "detalle_venta_lotes",
            "ajustes_inventario", "movimientos_inventario",
        }
        existing = {
            str(row[0])
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        missing = sorted(required_tables - existing)
        if missing:
            raise ValueError("El archivo seleccionado es una base SQLite válida, pero no corresponde a un respaldo del sistema.")

        required_columns = {
            "usuarios": {"id", "nombre", "usuario", "password_hash", "salt", "activo"},
            "productos": {"id", "nombre", "unidad_control", "precio", "stock_minimo", "activo"},
            "lotes": {"id", "producto_id", "entrada_id", "cantidad_inicial", "cantidad_actual", "fecha_vencimiento"},
            "ventas": {"id", "fecha_hora", "total", "estado", "usuario_id"},
        }
        for table, expected in required_columns.items():
            columns = {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
            if not expected.issubset(columns):
                raise ValueError("El archivo seleccionado no contiene la estructura esperada de un respaldo del sistema.")

    def _record(self, path: Path, kind: str, *, replace_same: bool = False) -> None:
        try:
            size = path.stat().st_size if path.exists() else 0
            with self.db.transaction() as con:
                if replace_same:
                    con.execute("DELETE FROM backup_historial WHERE ubicacion=? AND tipo=?", (str(path.resolve()), kind))
                con.execute(
                    "INSERT INTO backup_historial(archivo,ubicacion,tamano_bytes,tipo) VALUES (?,?,?,?)",
                    (path.name, str(path.resolve()), int(size), kind),
                )
        except Exception:
            # Un problema en el historial no debe invalidar una copia ya creada.
            pass

    def _copy_database(self, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        source = sqlite3.connect(self.db.path)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return destination

    def create_backup(
        self,
        destination: str | Path | None = None,
        *,
        record: bool = True,
        kind: str = "MANUAL",
    ) -> Path:
        if destination:
            destination = Path(destination)
            if destination.is_dir():
                destination = destination / f"inventario_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        else:
            destination = self.backup_dir / f"inventario_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        path = self._copy_database(destination)
        if record:
            self._record(path, kind)
        return path

    def automatic_backup(self) -> Path:
        """Actualiza la única copia de *último cierre* de la aplicación."""
        destination = self.backup_dir / "backup_ultimo_cierre.db"
        path = self._copy_database(destination)
        self._record(path, "AUTOMATICO_CIERRE", replace_same=True)
        return path

    def ensure_daily_automatic_backup(self) -> Path:
        """Crea una fotografía inmutable al inicio del día si aún no existe."""
        destination = self.backup_dir / f"backup_inicio_{datetime.now():%Y%m%d}.db"
        if destination.exists() and destination.stat().st_size > 0:
            return destination
        path = self._copy_database(destination)
        self._record(path, "AUTOMATICO_INICIO", replace_same=True)
        self.prune_automatic(self.AUTO_RETENTION_DAYS)
        return path

    def prune_automatic(self, keep_days: int = 7) -> None:
        """Conserva solo los snapshots de inicio de los últimos N días."""
        files = sorted(self.backup_dir.glob("backup_inicio_????????.db"), key=lambda p: p.name, reverse=True)
        for old in files[max(1, int(keep_days)):]:
            try:
                location = str(old.resolve())
                old.unlink(missing_ok=True)
                with self.db.transaction() as con:
                    con.execute("DELETE FROM backup_historial WHERE ubicacion=? AND tipo='AUTOMATICO_INICIO'", (location,))
            except Exception:
                pass

    def health_check(self) -> list[str]:
        issues: list[str] = []
        try:
            if self.db.integrity_check() != "ok":
                issues.append("La comprobación de integridad de la base de datos no devolvió OK.")
        except Exception as exc:
            issues.append(f"No fue posible comprobar la integridad de la base: {exc}")
            return issues
        try:
            if not self.db.required_tables_present():
                issues.append("Faltan tablas principales del sistema.")
            fk = self.db.foreign_key_violations()
            if fk:
                issues.append(f"Se detectaron {len(fk)} referencia(s) inconsistente(s) en la base de datos.")
        except Exception as exc:
            issues.append(f"No fue posible completar la revisión de estructura: {exc}")
        return issues

    def restore_backup(self, source_path: str | Path) -> Path:
        source_path = Path(source_path)
        if not source_path.exists():
            raise ValueError("El archivo de respaldo no existe.")

        check = sqlite3.connect(source_path)
        try:
            result = check.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise ValueError("El archivo seleccionado no es un respaldo válido.")
            self._validate_backup_schema(check)
        except sqlite3.DatabaseError as exc:
            raise ValueError("El archivo seleccionado no es un respaldo SQLite válido.") from exc
        finally:
            check.close()

        safety_path = self.backup_dir / f"antes_de_restaurar_{datetime.now():%Y%m%d_%H%M%S}.db"
        self.create_backup(safety_path, record=False)

        source = sqlite3.connect(source_path)
        target = sqlite3.connect(self.db.path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

        self.db.initialize()
        self._record(safety_path, "PREVIO_RESTAURACION")
        self._record(source_path, "RESTAURADO")
        return safety_path

    def history(self, limit: int = 10):
        with self.db.connect() as con:
            return con.execute(
                "SELECT id,fecha_hora,archivo,ubicacion,tamano_bytes,tipo FROM backup_historial ORDER BY id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
