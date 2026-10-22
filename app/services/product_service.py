from __future__ import annotations

import sqlite3

from ..database import Database
from .settings_service import SettingsService


class ProductService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.settings = SettingsService(db)

    def create_product(self, nombre: str, unidad_control: str, precio: float, stock_minimo: int, ubicacion: str = "") -> int:
        nombre = nombre.strip()
        unidad_control = unidad_control.strip()
        ubicacion = ubicacion.strip()
        if not nombre:
            raise ValueError("El nombre del producto es obligatorio.")
        if not unidad_control:
            raise ValueError("La unidad de control es obligatoria.")
        if precio < 0:
            raise ValueError("El precio no puede ser negativo.")
        if stock_minimo < 0:
            raise ValueError("El stock mínimo no puede ser negativo.")
        try:
            with self.db.transaction() as con:
                cur = con.execute(
                    """
                    INSERT INTO productos(nombre, unidad_control, precio, stock_minimo, ubicacion)
                    VALUES (?,?,?,?,?)
                    """,
                    (nombre, unidad_control, float(precio), int(stock_minimo), ubicacion or None),
                )
                return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            if "productos.nombre" in str(exc) or "UNIQUE constraint failed" in str(exc):
                raise ValueError("Ya existe un producto registrado con ese nombre.") from exc
            raise

    def update_product(self, product_id: int, nombre: str, unidad_control: str, precio: float, stock_minimo: int, ubicacion: str = "") -> None:
        nombre = nombre.strip()
        unidad_control = unidad_control.strip()
        if not nombre or not unidad_control:
            raise ValueError("Nombre y unidad de control son obligatorios.")
        if precio < 0 or stock_minimo < 0:
            raise ValueError("Precio y stock mínimo deben ser valores no negativos.")
        try:
            with self.db.transaction() as con:
                current = con.execute(
                    "SELECT id,unidad_control FROM productos WHERE id=?", (product_id,)
                ).fetchone()
                if not current:
                    raise ValueError("El producto no existe.")
                if current["unidad_control"] != unidad_control:
                    has_history = con.execute(
                        "SELECT EXISTS(SELECT 1 FROM lotes WHERE producto_id=? LIMIT 1)",
                        (product_id,),
                    ).fetchone()[0]
                    if has_history:
                        raise ValueError(
                            "No se puede cambiar la unidad de control porque el producto ya tiene historial de inventario. "
                            "Puede modificar el nombre, precio, mínimo o ubicación sin afectar la trazabilidad."
                        )
                con.execute(
                    """
                    UPDATE productos
                       SET nombre=?, unidad_control=?, precio=?, stock_minimo=?, ubicacion=?, actualizado_en=CURRENT_TIMESTAMP
                     WHERE id=?
                    """,
                    (nombre, unidad_control, float(precio), int(stock_minimo), ubicacion.strip() or None, product_id),
                )
        except sqlite3.IntegrityError as exc:
            if "productos.nombre" in str(exc) or "UNIQUE constraint failed" in str(exc):
                raise ValueError("Ya existe un producto registrado con ese nombre.") from exc
            raise


    def has_history(self, product_id: int) -> bool:
        with self.db.connect() as con:
            return bool(
                con.execute(
                    "SELECT EXISTS(SELECT 1 FROM lotes WHERE producto_id=? LIMIT 1)",
                    (product_id,),
                ).fetchone()[0]
            )

    def set_active(self, product_id: int, active: bool) -> None:
        with self.db.transaction() as con:
            product = con.execute("SELECT id,nombre,activo FROM productos WHERE id=?", (product_id,)).fetchone()
            if not product:
                raise ValueError("El producto no existe.")
            if not active:
                stock = int(
                    con.execute(
                        "SELECT COALESCE(SUM(cantidad_actual),0) FROM lotes WHERE producto_id=?",
                        (product_id,),
                    ).fetchone()[0]
                )
                if stock > 0:
                    raise ValueError(
                        f"No se puede desactivar {product['nombre']} porque todavía tiene {stock} unidad(es) registradas. "
                        "Primero venda, descarte o ajuste esas existencias."
                    )
            con.execute(
                "UPDATE productos SET activo=?, actualizado_en=CURRENT_TIMESTAMP WHERE id=?",
                (1 if active else 0, product_id),
            )

    def _stock_sql(self) -> str:
        return """
                   COALESCE(SUM(l.cantidad_actual),0) AS stock_total,
                   COALESCE(SUM(CASE
                       WHEN l.cantidad_actual > 0
                        AND (l.fecha_vencimiento IS NULL OR date(l.fecha_vencimiento) > date('now','localtime', ?))
                       THEN l.cantidad_actual ELSE 0 END),0) AS stock_vendible,
                   COALESCE(SUM(CASE
                       WHEN l.cantidad_actual > 0
                        AND l.fecha_vencimiento IS NOT NULL
                        AND date(l.fecha_vencimiento) >= date('now','localtime')
                        AND date(l.fecha_vencimiento) <= date('now','localtime', ?)
                       THEN l.cantidad_actual ELSE 0 END),0) AS stock_bloqueado,
                   COALESCE(SUM(CASE
                       WHEN l.cantidad_actual > 0
                        AND l.fecha_vencimiento IS NOT NULL
                        AND date(l.fecha_vencimiento) < date('now','localtime')
                       THEN l.cantidad_actual ELSE 0 END),0) AS stock_vencido
        """

    def list_products(self, include_inactive: bool = False):
        where = "" if include_inactive else "WHERE p.activo=1"
        query = f"""
            SELECT p.*,
                   {self._stock_sql()}
              FROM productos p
              LEFT JOIN lotes l ON l.producto_id=p.id
              {where}
             GROUP BY p.id
             ORDER BY p.nombre COLLATE NOCASE
        """
        cutoff = self.settings.get_block_days()
        with self.db.connect() as con:
            return con.execute(query, (f"+{cutoff} days", f"+{cutoff} days")).fetchall()

    def get_product(self, product_id: int):
        cutoff = self.settings.get_block_days()
        with self.db.connect() as con:
            return con.execute(
                f"""
                SELECT p.*,
                       {self._stock_sql()}
                  FROM productos p
                  LEFT JOIN lotes l ON l.producto_id=p.id
                 WHERE p.id=?
                 GROUP BY p.id
                """,
                (f"+{cutoff} days", f"+{cutoff} days", product_id),
            ).fetchone()

    def search(self, term: str):
        like = f"%{term.strip()}%"
        cutoff = self.settings.get_block_days()
        with self.db.connect() as con:
            return con.execute(
                f"""
                SELECT p.*,
                       {self._stock_sql()}
                  FROM productos p
                  LEFT JOIN lotes l ON l.producto_id=p.id
                 WHERE p.activo=1 AND p.nombre LIKE ? COLLATE NOCASE
                 GROUP BY p.id
                 ORDER BY p.nombre COLLATE NOCASE
                """,
                (f"+{cutoff} days", f"+{cutoff} days", like),
            ).fetchall()
