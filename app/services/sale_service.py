from __future__ import annotations

from datetime import date

from ..database import Database
from .settings_service import SettingsService
from .audit_service import AuditService


class SaleService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.settings = SettingsService(db)
        self.audit = AuditService(db)

    def _saleable_lots(self, con, product_id: int):
        return con.execute(
            """
            SELECT id,codigo_interno,cantidad_actual,fecha_vencimiento
              FROM lotes
             WHERE producto_id=?
               AND cantidad_actual > 0
               AND (fecha_vencimiento IS NULL OR date(fecha_vencimiento) > date('now','localtime', ?))
             ORDER BY CASE WHEN fecha_vencimiento IS NULL THEN 1 ELSE 0 END,
                      date(fecha_vencimiento) ASC,
                      id ASC
            """,
            (product_id, f"+{self.settings.get_block_days()} days"),
        ).fetchall()

    def create_sale(self, items: list[dict], user_id: int) -> int:
        if not items:
            raise ValueError("La venta debe contener al menos un producto.")

        # Consolidar líneas repetidas del mismo producto evita que dos renglones
        # independientes validen contra el mismo stock antes de descontarlo.
        # La interfaz ya agrupa productos, pero el servicio también debe proteger
        # la integridad si recibe datos duplicados desde pruebas o futuras vistas.
        quantities_by_product: dict[int, int] = {}
        for item in items:
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])
            if quantity <= 0:
                raise ValueError("Las cantidades de la venta deben ser mayores que cero.")
            quantities_by_product[product_id] = quantities_by_product.get(product_id, 0) + quantity
        normalized = [
            {"product_id": product_id, "quantity": quantity}
            for product_id, quantity in quantities_by_product.items()
        ]

        with self.db.transaction() as con:
            prepared: list[dict] = []
            total = 0.0

            for item in normalized:
                product = con.execute(
                    "SELECT id,nombre,precio,activo FROM productos WHERE id=?",
                    (item["product_id"],),
                ).fetchone()
                if not product or not product["activo"]:
                    raise ValueError("Uno de los productos no existe o está inactivo.")

                lots = self._saleable_lots(con, product["id"])
                available = sum(int(l["cantidad_actual"]) for l in lots)
                if available < item["quantity"]:
                    raise ValueError(
                        f"Stock insuficiente de {product['nombre']}. Disponible para venta: {available}."
                    )

                remaining = item["quantity"]
                allocations: list[tuple[int, int]] = []
                for lot in lots:
                    if remaining <= 0:
                        break
                    take = min(remaining, int(lot["cantidad_actual"]))
                    if take:
                        allocations.append((int(lot["id"]), take))
                        remaining -= take

                unit_price = float(product["precio"])
                subtotal = round(unit_price * item["quantity"], 2)
                total = round(total + subtotal, 2)
                prepared.append(
                    {
                        "product": product,
                        "quantity": item["quantity"],
                        "unit_price": unit_price,
                        "subtotal": subtotal,
                        "allocations": allocations,
                    }
                )

            sale_cur = con.execute(
                "INSERT INTO ventas(total,usuario_id) VALUES (?,?)",
                (total, user_id),
            )
            sale_id = int(sale_cur.lastrowid)

            for item in prepared:
                detail_cur = con.execute(
                    """
                    INSERT INTO detalle_ventas(venta_id,producto_id,cantidad,precio_unitario,subtotal)
                    VALUES (?,?,?,?,?)
                    """,
                    (
                        sale_id,
                        item["product"]["id"],
                        item["quantity"],
                        item["unit_price"],
                        item["subtotal"],
                    ),
                )
                detail_id = int(detail_cur.lastrowid)

                for lot_id, qty in item["allocations"]:
                    cur = con.execute(
                        "UPDATE lotes SET cantidad_actual=cantidad_actual-? WHERE id=? AND cantidad_actual>=?",
                        (qty, lot_id, qty),
                    )
                    if cur.rowcount != 1:
                        raise RuntimeError("El inventario cambió durante la venta. Actualice la pantalla e inténtelo nuevamente.")
                    con.execute(
                        "INSERT INTO detalle_venta_lotes(detalle_venta_id,lote_id,cantidad) VALUES (?,?,?)",
                        (detail_id, lot_id, qty),
                    )
                    con.execute(
                        """
                        INSERT INTO movimientos_inventario(
                            producto_id,lote_id,tipo,cantidad,referencia_tipo,referencia_id,usuario_id
                        ) VALUES (?,?, 'VENTA', ?, 'VENTA', ?, ?)
                        """,
                        (item["product"]["id"], lot_id, -qty, sale_id, user_id),
                    )

        return sale_id

    def cancel_sale(self, sale_id: int, reason: str, user_id: int) -> None:
        reason = reason.strip()
        if not reason:
            raise ValueError("Debe indicar el motivo de la anulación.")

        with self.db.transaction() as con:
            sale = con.execute("SELECT * FROM ventas WHERE id=?", (sale_id,)).fetchone()
            if not sale:
                raise ValueError("La venta no existe.")
            if sale["estado"] == "ANULADA":
                raise ValueError("La venta ya fue anulada.")

            allocations = con.execute(
                """
                SELECT d.producto_id, dl.lote_id, dl.cantidad
                  FROM detalle_ventas d
                  JOIN detalle_venta_lotes dl ON dl.detalle_venta_id=d.id
                 WHERE d.venta_id=?
                """,
                (sale_id,),
            ).fetchall()

            for row in allocations:
                con.execute(
                    "UPDATE lotes SET cantidad_actual=cantidad_actual+? WHERE id=?",
                    (row["cantidad"], row["lote_id"]),
                )
                con.execute(
                    """
                    INSERT INTO movimientos_inventario(
                        producto_id,lote_id,tipo,cantidad,referencia_tipo,referencia_id,usuario_id,motivo
                    ) VALUES (?,?, 'ANULACION', ?, 'VENTA', ?, ?, ?)
                    """,
                    (row["producto_id"], row["lote_id"], row["cantidad"], sale_id, user_id, reason),
                )

            con.execute(
                """
                UPDATE ventas
                   SET estado='ANULADA', motivo_anulacion=?, fecha_anulacion=CURRENT_TIMESTAMP
                 WHERE id=?
                """,
                (reason, sale_id),
            )

        self.audit.log("ANULAR_VENTA", user_id=user_id, entity="VENTA", entity_id=sale_id, detail=reason)

    def list_sales(self, limit: int = 200):
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT v.id,v.fecha_hora,v.total,v.estado,v.motivo_anulacion,u.nombre AS usuario
                  FROM ventas v
                  JOIN usuarios u ON u.id=v.usuario_id
                 ORDER BY v.id DESC
                 LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

    def get_sale_details(self, sale_id: int):
        with self.db.connect() as con:
            sale = con.execute(
                """
                SELECT v.*,u.nombre AS usuario
                  FROM ventas v JOIN usuarios u ON u.id=v.usuario_id
                 WHERE v.id=?
                """,
                (sale_id,),
            ).fetchone()
            items = con.execute(
                """
                SELECT d.id,d.cantidad,d.precio_unitario,d.subtotal,p.nombre,p.unidad_control
                  FROM detalle_ventas d
                  JOIN productos p ON p.id=d.producto_id
                 WHERE d.venta_id=?
                 ORDER BY d.id
                """,
                (sale_id,),
            ).fetchall()
            return sale, items
