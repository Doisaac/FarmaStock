from __future__ import annotations

from ..database import Database
from .settings_service import SettingsService
from .audit_service import AuditService


class InventoryService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.settings = SettingsService(db)
        self.audit = AuditService(db)

    def inventory_rows(self):
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT p.id,p.nombre,p.unidad_control,p.precio,p.stock_minimo,p.ubicacion,p.activo,
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
                  FROM productos p
                  LEFT JOIN lotes l ON l.producto_id=p.id
                 WHERE p.activo=1
                 GROUP BY p.id
                 ORDER BY p.nombre COLLATE NOCASE
                """,
                (f"+{self.settings.get_block_days()} days", f"+{self.settings.get_block_days()} days"),
            ).fetchall()

    def lots_for_product(self, product_id: int, include_empty: bool = True):
        where_empty = "" if include_empty else "AND l.cantidad_actual > 0"
        with self.db.connect() as con:
            return con.execute(
                f"""
                SELECT l.*, p.nombre, p.unidad_control
                  FROM lotes l
                  JOIN productos p ON p.id=l.producto_id
                 WHERE l.producto_id=? {where_empty}
                 ORDER BY CASE WHEN l.fecha_vencimiento IS NULL THEN 1 ELSE 0 END,
                          date(l.fecha_vencimiento), l.id
                """,
                (product_id,),
            ).fetchall()

    def low_stock(self):
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT p.id,p.nombre,p.unidad_control,p.stock_minimo,
                       COALESCE(SUM(CASE
                           WHEN l.cantidad_actual > 0
                            AND (l.fecha_vencimiento IS NULL OR date(l.fecha_vencimiento) > date('now','localtime', ?))
                           THEN l.cantidad_actual ELSE 0 END),0) AS stock_vendible
                  FROM productos p
                  LEFT JOIN lotes l ON l.producto_id=p.id
                 WHERE p.activo=1
                 GROUP BY p.id
                HAVING stock_vendible <= p.stock_minimo
                 ORDER BY stock_vendible ASC, p.nombre COLLATE NOCASE
                """,
                (f"+{self.settings.get_block_days()} days",),
            ).fetchall()

    def expiring(self, days: int = 90):
        days = max(0, int(days))
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT l.id,l.codigo_interno,l.lote_fabricante,l.cantidad_actual,l.fecha_vencimiento,
                       p.id AS producto_id,p.nombre,p.unidad_control,
                       CAST(julianday(l.fecha_vencimiento)-julianday(date('now','localtime')) AS INTEGER) AS dias_restantes
                  FROM lotes l
                  JOIN productos p ON p.id=l.producto_id
                 WHERE l.cantidad_actual > 0
                   AND l.fecha_vencimiento IS NOT NULL
                   AND date(l.fecha_vencimiento) >= date('now','localtime')
                   AND date(l.fecha_vencimiento) <= date('now','localtime', ?)
                 ORDER BY date(l.fecha_vencimiento), p.nombre COLLATE NOCASE
                """,
                (f"+{days} days",),
            ).fetchall()

    def expired(self):
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT l.id,l.codigo_interno,l.lote_fabricante,l.cantidad_actual,l.fecha_vencimiento,
                       p.id AS producto_id,p.nombre,p.unidad_control
                  FROM lotes l
                  JOIN productos p ON p.id=l.producto_id
                 WHERE l.cantidad_actual > 0
                   AND l.fecha_vencimiento IS NOT NULL
                   AND date(l.fecha_vencimiento) < date('now','localtime')
                 ORDER BY date(l.fecha_vencimiento), p.nombre COLLATE NOCASE
                """
            ).fetchall()

    def adjust_lot(self, lot_id: int, physical_qty: int, reason: str, user_id: int) -> int:
        physical_qty = int(physical_qty)
        reason = reason.strip()
        if physical_qty < 0:
            raise ValueError("La cantidad física no puede ser negativa.")
        if not reason:
            raise ValueError("Debe indicar el motivo del ajuste.")

        with self.db.transaction() as con:
            lot = con.execute(
                "SELECT id,producto_id,cantidad_actual FROM lotes WHERE id=?", (lot_id,)
            ).fetchone()
            if not lot:
                raise ValueError("El lote seleccionado no existe.")
            system_qty = int(lot["cantidad_actual"])
            difference = physical_qty - system_qty
            if difference == 0:
                raise ValueError("La cantidad física coincide con la registrada; no se requiere ajuste.")

            cur = con.execute(
                """
                INSERT INTO ajustes_inventario(
                    producto_id,lote_id,cantidad_sistema,cantidad_fisica,diferencia,motivo,usuario_id
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (lot["producto_id"], lot_id, system_qty, physical_qty, difference, reason, user_id),
            )
            adjustment_id = int(cur.lastrowid)
            con.execute("UPDATE lotes SET cantidad_actual=? WHERE id=?", (physical_qty, lot_id))
            con.execute(
                """
                INSERT INTO movimientos_inventario(
                    producto_id,lote_id,tipo,cantidad,referencia_tipo,referencia_id,usuario_id,motivo
                ) VALUES (?,?, 'AJUSTE', ?, 'AJUSTE', ?, ?, ?)
                """,
                (lot["producto_id"], lot_id, difference, adjustment_id, user_id, reason),
            )
        self.audit.log(
            "AJUSTE_INVENTARIO",
            user_id=user_id,
            entity="LOTE",
            entity_id=lot_id,
            detail=f"{system_qty} → {physical_qty}. {reason}",
        )
        return adjustment_id

    def discard_expired(self, lot_id: int, quantity: int, reason: str, user_id: int) -> int:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("La cantidad a descartar debe ser mayor que cero.")
        reason = reason.strip()
        if not reason:
            raise ValueError("Debe indicar el motivo de la merma o descarte.")
        with self.db.connect() as con:
            lot = con.execute(
                """
                SELECT l.id,l.cantidad_actual,l.fecha_vencimiento,p.nombre
                  FROM lotes l JOIN productos p ON p.id=l.producto_id
                 WHERE l.id=?
                """,
                (lot_id,),
            ).fetchone()
        if not lot:
            raise ValueError("El lote no existe.")
        if not lot["fecha_vencimiento"]:
            raise ValueError("El lote seleccionado no tiene fecha de vencimiento.")
        with self.db.connect() as con:
            is_expired = con.execute("SELECT date(?) < date('now','localtime')", (lot["fecha_vencimiento"],)).fetchone()[0]
        if not is_expired:
            raise ValueError("Solo se puede registrar esta merma desde Alertas para lotes vencidos.")
        if quantity > int(lot["cantidad_actual"]):
            raise ValueError(f"La cantidad supera la existencia del lote ({lot['cantidad_actual']}).")
        new_qty = int(lot["cantidad_actual"]) - quantity
        adjustment_id = self.adjust_lot(lot_id, new_qty, f"Merma por vencimiento: {reason}", user_id)
        self.audit.log(
            "MERMA_VENCIMIENTO",
            user_id=user_id,
            entity="LOTE",
            entity_id=lot_id,
            detail=f"Cantidad: {quantity}. {reason}",
        )
        return adjustment_id

    def movements(self, start: str | None = None, end: str | None = None, product_id: int | None = None):
        clauses = []
        params: list[object] = []
        if start:
            clauses.append("date(m.fecha_hora,'localtime') >= date(?)")
            params.append(start)
        if end:
            clauses.append("date(m.fecha_hora,'localtime') <= date(?)")
            params.append(end)
        if product_id:
            clauses.append("m.producto_id=?")
            params.append(product_id)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        with self.db.connect() as con:
            return con.execute(
                f"""
                SELECT m.id,m.fecha_hora,p.nombre,p.unidad_control,l.codigo_interno,m.tipo,
                       m.cantidad,m.referencia_tipo,m.referencia_id,m.motivo,u.nombre AS usuario
                  FROM movimientos_inventario m
                  JOIN productos p ON p.id=m.producto_id
                  LEFT JOIN lotes l ON l.id=m.lote_id
                  JOIN usuarios u ON u.id=m.usuario_id
                  {where}
                 ORDER BY m.id DESC
                """,
                params,
            ).fetchall()
