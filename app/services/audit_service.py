from __future__ import annotations

from ..database import Database


class AuditService:
    """Registro liviano de operaciones sensibles.

    La auditoría no interrumpe la operación principal: si por alguna razón no
    puede escribirse el registro, la acción de negocio ya completada no se
    revierte ni se bloquea.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def log(
        self,
        action: str,
        *,
        user_id: int | None = None,
        entity: str | None = None,
        entity_id: int | None = None,
        detail: str | None = None,
    ) -> None:
        try:
            with self.db.transaction() as con:
                con.execute(
                    """
                    INSERT INTO auditoria(usuario_id,accion,entidad,entidad_id,detalle)
                    VALUES (?,?,?,?,?)
                    """,
                    (user_id, action, entity, entity_id, detail),
                )
        except Exception:
            pass

    def recent(self, limit: int = 100):
        with self.db.connect() as con:
            return con.execute(
                """
                SELECT a.id,a.fecha_hora,a.accion,a.entidad,a.entidad_id,a.detalle,
                       u.nombre AS usuario
                  FROM auditoria a
                  LEFT JOIN usuarios u ON u.id=a.usuario_id
                 ORDER BY a.id DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
