from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import DB_PATH, ensure_directories



class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    rol TEXT NOT NULL DEFAULT 'OPERADOR',
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE COLLATE NOCASE,
    unidad_control TEXT NOT NULL,
    precio REAL NOT NULL DEFAULT 0 CHECK (precio >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    ubicacion TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS entradas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_id INTEGER NOT NULL,
    observacion TEXT,
    estado TEXT NOT NULL DEFAULT 'ACTIVA',
    motivo_anulacion TEXT,
    fecha_anulacion TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL,
    entrada_id INTEGER NOT NULL,
    correlativo INTEGER NOT NULL,
    codigo_interno TEXT NOT NULL UNIQUE,
    lote_fabricante TEXT,
    cantidad_inicial INTEGER NOT NULL CHECK (cantidad_inicial >= 0),
    cantidad_actual INTEGER NOT NULL CHECK (cantidad_actual >= 0),
    fecha_vencimiento TEXT,
    fecha_ingreso TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(producto_id, correlativo),
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (entrada_id) REFERENCES entradas(id)
);

CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total REAL NOT NULL CHECK (total >= 0),
    estado TEXT NOT NULL DEFAULT 'CONFIRMADA' CHECK (estado IN ('CONFIRMADA','ANULADA')),
    usuario_id INTEGER NOT NULL,
    motivo_anulacion TEXT,
    fecha_anulacion TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS detalle_ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL,
    producto_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
    subtotal REAL NOT NULL CHECK (subtotal >= 0),
    FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE TABLE IF NOT EXISTS detalle_venta_lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detalle_venta_id INTEGER NOT NULL,
    lote_id INTEGER NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    FOREIGN KEY (detalle_venta_id) REFERENCES detalle_ventas(id) ON DELETE CASCADE,
    FOREIGN KEY (lote_id) REFERENCES lotes(id)
);

CREATE TABLE IF NOT EXISTS ajustes_inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    producto_id INTEGER NOT NULL,
    lote_id INTEGER NOT NULL,
    cantidad_sistema INTEGER NOT NULL,
    cantidad_fisica INTEGER NOT NULL CHECK (cantidad_fisica >= 0),
    diferencia INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    usuario_id INTEGER NOT NULL,
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (lote_id) REFERENCES lotes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    producto_id INTEGER NOT NULL,
    lote_id INTEGER,
    tipo TEXT NOT NULL CHECK (tipo IN ('ENTRADA','VENTA','ANULACION','AJUSTE')),
    cantidad INTEGER NOT NULL,
    referencia_tipo TEXT,
    referencia_id INTEGER,
    usuario_id INTEGER NOT NULL,
    motivo TEXT,
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (lote_id) REFERENCES lotes(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);


CREATE TABLE IF NOT EXISTS configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS backup_historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    archivo TEXT NOT NULL,
    ubicacion TEXT NOT NULL,
    tamano_bytes INTEGER NOT NULL DEFAULT 0,
    tipo TEXT NOT NULL DEFAULT 'CREADO'
);

CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    usuario_id INTEGER,
    accion TEXT NOT NULL,
    entidad TEXT,
    entidad_id INTEGER,
    detalle TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_lotes_producto ON lotes(producto_id);
CREATE INDEX IF NOT EXISTS idx_lotes_vencimiento ON lotes(fecha_vencimiento);
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos_inventario(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_movimientos_producto ON movimientos_inventario(producto_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria(fecha_hora);
"""


class Database:
    def __init__(self, path: Path | str | None = None) -> None:
        ensure_directories()
        self.path = Path(path) if path else DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30, factory=ClosingConnection)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        con.execute("PRAGMA journal_mode = WAL")
        return con

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        con = self.connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def _column_names(con: sqlite3.Connection, table: str) -> set[str]:
        return {str(r["name"]) for r in con.execute(f"PRAGMA table_info({table})").fetchall()}

    def _migrate(self, con: sqlite3.Connection) -> None:
        user_cols = self._column_names(con, "usuarios")
        if "rol" not in user_cols:
            con.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'OPERADOR'")
        con.execute("UPDATE usuarios SET rol='ADMIN' WHERE usuario='admin' COLLATE NOCASE")
        con.execute("UPDATE usuarios SET rol='OPERADOR' WHERE rol IS NULL OR trim(rol)='' OR rol NOT IN ('ADMIN','OPERADOR')")

        entry_cols = self._column_names(con, "entradas")
        if "estado" not in entry_cols:
            con.execute("ALTER TABLE entradas ADD COLUMN estado TEXT NOT NULL DEFAULT 'ACTIVA'")
        if "motivo_anulacion" not in entry_cols:
            con.execute("ALTER TABLE entradas ADD COLUMN motivo_anulacion TEXT")
        if "fecha_anulacion" not in entry_cols:
            con.execute("ALTER TABLE entradas ADD COLUMN fecha_anulacion TEXT")

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL,
                actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        con.execute(
            "INSERT OR IGNORE INTO configuracion(clave,valor) VALUES ('dias_bloqueo_venta_vencimiento','15')"
        )
        con.execute("INSERT OR IGNORE INTO configuracion(clave,valor) VALUES ('tema_apariencia','dark')")
        con.execute("INSERT OR IGNORE INTO configuracion(clave,valor) VALUES ('minutos_bloqueo_inactividad','0')")

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS backup_historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                archivo TEXT NOT NULL,
                ubicacion TEXT NOT NULL,
                tamano_bytes INTEGER NOT NULL DEFAULT 0,
                tipo TEXT NOT NULL DEFAULT 'CREADO'
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                usuario_id INTEGER,
                accion TEXT NOT NULL,
                entidad TEXT,
                entidad_id INTEGER,
                detalle TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria(fecha_hora)")

    def initialize(self) -> None:
        with self.connect() as con:
            con.executescript(SCHEMA)
            self._migrate(con)
            con.commit()

    def integrity_check(self) -> str:
        with self.connect() as con:
            return con.execute("PRAGMA integrity_check").fetchone()[0]

    def foreign_key_violations(self) -> list:
        with self.connect() as con:
            return con.execute("PRAGMA foreign_key_check").fetchall()

    def required_tables_present(self) -> bool:
        required = {"usuarios", "productos", "entradas", "lotes", "ventas", "movimientos_inventario"}
        with self.connect() as con:
            found = {str(r[0]) for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        return required.issubset(found)
