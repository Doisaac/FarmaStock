from __future__ import annotations

from datetime import date

from ..database import Database
from .audit_service import AuditService


class EntryService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.audit = AuditService(db)

    @staticmethod
    def _normalize_date(value: str | None) -> str | None:
        if not value:
            return None
        value = value.strip()
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValueError("La fecha de vencimiento no es válida.") from exc

    def register_entry(
        self,
        product_id: int,
        quantity: int,
        expiration_date: str | None,
        user_id: int,
        manufacturer_lot: str = "",
        notes: str = "",
    ) -> dict:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("La cantidad recibida debe ser mayor que cero.")
        expiration = self._normalize_date(expiration_date)
        manufacturer_lot = manufacturer_lot.strip() or None
        notes = notes.strip() or None

        with self.db.transaction() as con:
            product = con.execute(
                "SELECT id,nombre,activo FROM productos WHERE id=?", (product_id,)
            ).fetchone()
            if not product or not product["activo"]:
                raise ValueError("El producto seleccionado no existe o está inactivo.")

            entry_cur = con.execute(
                "INSERT INTO entradas(usuario_id, observacion, estado) VALUES (?,?,'ACTIVA')",
                (user_id, notes),
            )
            entry_id = int(entry_cur.lastrowid)

            next_seq = con.execute(
                "SELECT COALESCE(MAX(correlativo),0)+1 FROM lotes WHERE producto_id=?",
                (product_id,),
            ).fetchone()[0]
            internal_code = f"P{product_id:04d}-L{int(next_seq):03d}"

            lot_cur = con.execute(
                """
                INSERT INTO lotes(
                    producto_id, entrada_id, correlativo, codigo_interno, lote_fabricante,
                    cantidad_inicial, cantidad_actual, fecha_vencimiento
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    product_id,
                    entry_id,
                    int(next_seq),
                    internal_code,
                    manufacturer_lot,
                    quantity,
                    quantity,
                    expiration,
                ),
            )
            lot_id = int(lot_cur.lastrowid)

            con.execute(
                """
                INSERT INTO movimientos_inventario(
                    producto_id,lote_id,tipo,cantidad,referencia_tipo,referencia_id,usuario_id,motivo
                ) VALUES (?,?, 'ENTRADA', ?, 'ENTRADA', ?, ?, ?)
                """,
                (product_id, lot_id, quantity, entry_id, user_id, notes),
            )

        return {
            "entry_id": entry_id,
            "lot_id": lot_id,
            "internal_code": internal_code,
            "quantity": quantity,
            "expiration_date": expiration,
        }

    def list_entries(self, limit: int = 200):
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT e.id, e.fecha_hora, e.estado, e.motivo_anulacion, e.fecha_anulacion,
                       p.id AS producto_id, p.nombre AS producto, p.unidad_control,
                       l.id AS lote_id, l.codigo_interno, l.lote_fabricante, l.cantidad_inicial,
                       l.cantidad_actual, l.fecha_vencimiento, u.nombre AS usuario,
                       e.observacion,
                       CASE WHEN e.estado='ACTIVA'
                                  AND l.cantidad_actual=l.cantidad_inicial
                                  AND NOT EXISTS(SELECT 1 FROM detalle_venta_lotes dvl WHERE dvl.lote_id=l.id)
                                  AND NOT EXISTS(SELECT 1 FROM ajustes_inventario ai WHERE ai.lote_id=l.id)
                            THEN 1 ELSE 0 END AS puede_anular
                  FROM entradas e
                  JOIN lotes l ON l.entrada_id=e.id
                  JOIN productos p ON p.id=l.producto_id
                  JOIN usuarios u ON u.id=e.usuario_id
                 ORDER BY e.id DESC
                 LIMIT ?
                """,
                (int(limit),),
            ).fetchall()

    def update_entry_metadata(self, entry_id: int, manufacturer_lot: str, observation: str) -> None:
        """Corrige datos descriptivos sin modificar cantidades ni vencimientos.

        El lote del fabricante y la observación no alteran la existencia, por lo
        que pueden corregirse sin rehacer una entrada. Las cantidades y fechas
        siguen protegidas por el historial de movimientos.
        """
        manufacturer_lot = manufacturer_lot.strip() or None
        observation = observation.strip() or None
        with self.db.transaction() as con:
            row = con.execute(
                """
                SELECT e.id,e.estado,l.id AS lote_id
                  FROM entradas e
                  JOIN lotes l ON l.entrada_id=e.id
                 WHERE e.id=?
                """,
                (entry_id,),
            ).fetchone()
            if not row:
                raise ValueError("La entrada no existe.")
            if row["estado"] == "ANULADA":
                raise ValueError("Una entrada anulada se conserva únicamente como historial y ya no puede editarse.")
            con.execute("UPDATE entradas SET observacion=? WHERE id=?", (observation, entry_id))
            con.execute("UPDATE lotes SET lote_fabricante=? WHERE id=?", (manufacturer_lot, row["lote_id"]))

    def update_observation(self, entry_id: int, observation: str) -> None:
        # Compatibilidad con llamadas de versiones anteriores.
        with self.db.connect() as con:
            row = con.execute(
                "SELECT lote_fabricante FROM lotes WHERE entrada_id=?",
                (entry_id,),
            ).fetchone()
        manufacturer_lot = row["lote_fabricante"] if row else ""
        self.update_entry_metadata(entry_id, manufacturer_lot or "", observation)

    def cancel_entry(self, entry_id: int, reason: str, user_id: int) -> None:
        reason = reason.strip()
        if not reason:
            raise ValueError("Debe indicar el motivo de la anulación.")

        with self.db.transaction() as con:
            row = con.execute(
                """
                SELECT e.id,e.estado,l.id AS lote_id,l.producto_id,l.cantidad_inicial,l.cantidad_actual
                  FROM entradas e JOIN lotes l ON l.entrada_id=e.id
                 WHERE e.id=?
                """,
                (entry_id,),
            ).fetchone()
            if not row:
                raise ValueError("La entrada no existe.")
            if row["estado"] == "ANULADA":
                raise ValueError("La entrada ya fue anulada.")

            used_in_sales = con.execute(
                "SELECT COUNT(*) FROM detalle_venta_lotes WHERE lote_id=?",
                (row["lote_id"],),
            ).fetchone()[0]
            adjustments = con.execute(
                "SELECT COUNT(*) FROM ajustes_inventario WHERE lote_id=?",
                (row["lote_id"],),
            ).fetchone()[0]
            if used_in_sales or adjustments or int(row["cantidad_actual"]) != int(row["cantidad_inicial"]):
                raise ValueError(
                    "Esta entrada ya tuvo movimientos posteriores. Para conservar la trazabilidad no puede anularse; use un ajuste de inventario si necesita corregir la existencia."
                )

            qty = int(row["cantidad_actual"])
            con.execute("UPDATE lotes SET cantidad_actual=0 WHERE id=?", (row["lote_id"],))
            con.execute(
                """
                UPDATE entradas
                   SET estado='ANULADA', motivo_anulacion=?, fecha_anulacion=CURRENT_TIMESTAMP
                 WHERE id=?
                """,
                (reason, entry_id),
            )
            con.execute(
                """
                INSERT INTO movimientos_inventario(
                    producto_id,lote_id,tipo,cantidad,referencia_tipo,referencia_id,usuario_id,motivo
                ) VALUES (?,?, 'AJUSTE', ?, 'ENTRADA', ?, ?, ?)
                """,
                (row["producto_id"], row["lote_id"], -qty, entry_id, user_id, f"Anulación de entrada: {reason}"),
            )

        self.audit.log("ANULAR_ENTRADA", user_id=user_id, entity="ENTRADA", entity_id=entry_id, detail=reason)
