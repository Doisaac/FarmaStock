from __future__ import annotations

from ..database import Database
from .settings_service import SettingsService


class DashboardService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.settings = SettingsService(db)

    def summary(self) -> dict:
        with self.db.connect() as con:
            products = con.execute("SELECT COUNT(*) FROM productos WHERE activo=1").fetchone()[0]
            sales_today = con.execute(
                "SELECT COUNT(*) FROM ventas WHERE estado='CONFIRMADA' AND date(fecha_hora,'localtime')=date('now','localtime')"
            ).fetchone()[0]
            sales_total_today = con.execute(
                "SELECT COALESCE(SUM(total),0) FROM ventas WHERE estado='CONFIRMADA' AND date(fecha_hora,'localtime')=date('now','localtime')"
            ).fetchone()[0]
            cutoff = self.settings.get_block_days()
            low_stock = con.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT p.id,p.stock_minimo,
                           COALESCE(SUM(CASE WHEN l.cantidad_actual>0
                             AND (l.fecha_vencimiento IS NULL OR date(l.fecha_vencimiento)>date('now','localtime', ?))
                             THEN l.cantidad_actual ELSE 0 END),0) stock
                      FROM productos p LEFT JOIN lotes l ON l.producto_id=p.id
                     WHERE p.activo=1 GROUP BY p.id HAVING stock <= p.stock_minimo
                )
                """,
                (f"+{cutoff} days",),
            ).fetchone()[0]
            expiring = con.execute(
                """
                SELECT COUNT(*) FROM lotes
                 WHERE cantidad_actual>0 AND fecha_vencimiento IS NOT NULL
                   AND date(fecha_vencimiento)>=date('now','localtime')
                   AND date(fecha_vencimiento)<=date('now','localtime','+90 days')
                """
            ).fetchone()[0]
            expired = con.execute(
                """
                SELECT COUNT(*) FROM lotes
                 WHERE cantidad_actual>0 AND fecha_vencimiento IS NOT NULL
                   AND date(fecha_vencimiento)<date('now','localtime')
                """
            ).fetchone()[0]
        return {
            "products": int(products),
            "sales_today": int(sales_today),
            "sales_total_today": float(sales_total_today),
            "low_stock": int(low_stock),
            "expiring": int(expiring),
            "expired": int(expired),
        }

    def latest_sales(self, limit: int = 5):
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT v.id,v.fecha_hora,v.total,v.estado,u.nombre AS usuario
                  FROM ventas v JOIN usuarios u ON u.id=v.usuario_id
                 ORDER BY v.id DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
