from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from ..database import Database
from ..security import hash_password, verify_password


@dataclass(frozen=True)
class UserSession:
    id: int
    nombre: str
    usuario: str
    rol: str

    @property
    def is_admin(self) -> bool:
        return self.rol == "ADMIN"


class AuthService:
    VALID_ROLES = {"ADMIN", "OPERADOR"}

    def __init__(self, db: Database) -> None:
        self.db = db

    def ensure_default_admin(self) -> None:
        with self.db.transaction() as con:
            count = con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
            if count == 0:
                password_hash, salt = hash_password("Admin123!")
                con.execute(
                    "INSERT INTO usuarios(nombre, usuario, password_hash, salt, rol) VALUES (?,?,?,?,?)",
                    ("Administrador", "admin", password_hash, salt, "ADMIN"),
                )
            else:
                con.execute("UPDATE usuarios SET rol='ADMIN' WHERE usuario='admin' COLLATE NOCASE")

    def login(self, username: str, password: str) -> UserSession | None:
        username = username.strip()
        if not username or not password:
            return None
        with self.db.connect() as con:
            row = con.execute(
                "SELECT id,nombre,usuario,password_hash,salt,activo,rol FROM usuarios WHERE usuario=? COLLATE NOCASE",
                (username,),
            ).fetchone()
        if not row or not row["activo"]:
            return None
        if not verify_password(password, row["password_hash"], row["salt"]):
            return None
        return UserSession(id=row["id"], nombre=row["nombre"], usuario=row["usuario"], rol=row["rol"])

    def list_users(self):
        with self.db.connect() as con:
            return con.execute(
                "SELECT id,nombre,usuario,rol,activo,creado_en FROM usuarios ORDER BY nombre"
            ).fetchall()

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")

    def create_user(self, nombre: str, usuario: str, password: str, role: str = "OPERADOR") -> int:
        nombre, usuario = nombre.strip(), usuario.strip()
        role = role.strip().upper()
        if not nombre or not usuario or not password:
            raise ValueError("Nombre, usuario y contraseña son obligatorios.")
        if role not in self.VALID_ROLES:
            raise ValueError("El rol seleccionado no es válido.")
        self._validate_password(password)
        password_hash, salt = hash_password(password)
        try:
            with self.db.transaction() as con:
                cur = con.execute(
                    "INSERT INTO usuarios(nombre,usuario,password_hash,salt,rol) VALUES (?,?,?,?,?)",
                    (nombre, usuario, password_hash, salt, role),
                )
                return int(cur.lastrowid)
        except sqlite3.IntegrityError as exc:
            if "usuarios.usuario" in str(exc) or "UNIQUE constraint failed" in str(exc):
                raise ValueError("Ese nombre de usuario ya está registrado.") from exc
            raise

    def update_user(self, user_id: int, nombre: str, usuario: str, role: str) -> None:
        nombre, usuario, role = nombre.strip(), usuario.strip(), role.strip().upper()
        if not nombre or not usuario:
            raise ValueError("Nombre y usuario son obligatorios.")
        if role not in self.VALID_ROLES:
            raise ValueError("El rol seleccionado no es válido.")
        with self.db.transaction() as con:
            current = con.execute("SELECT id,rol,activo FROM usuarios WHERE id=?", (user_id,)).fetchone()
            if not current:
                raise ValueError("El usuario no existe.")
            if current["rol"] == "ADMIN" and role != "ADMIN" and current["activo"]:
                active_admins = con.execute("SELECT COUNT(*) FROM usuarios WHERE rol='ADMIN' AND activo=1").fetchone()[0]
                if active_admins <= 1:
                    raise ValueError("No se puede quitar el rol al único administrador activo.")
            try:
                con.execute("UPDATE usuarios SET nombre=?,usuario=?,rol=? WHERE id=?", (nombre, usuario, role, user_id))
            except sqlite3.IntegrityError as exc:
                if "usuarios.usuario" in str(exc) or "UNIQUE constraint failed" in str(exc):
                    raise ValueError("Ese nombre de usuario ya está registrado.") from exc
                raise

    def change_password(self, user_id: int, new_password: str) -> None:
        self._validate_password(new_password)
        password_hash, salt = hash_password(new_password)
        with self.db.transaction() as con:
            con.execute(
                "UPDATE usuarios SET password_hash=?, salt=? WHERE id=?",
                (password_hash, salt, user_id),
            )

    def set_active(self, user_id: int, active: bool) -> None:
        with self.db.transaction() as con:
            user = con.execute("SELECT id,rol,activo FROM usuarios WHERE id=?", (user_id,)).fetchone()
            if not user:
                raise ValueError("El usuario no existe.")
            if not active and user["rol"] == "ADMIN" and user["activo"]:
                active_admins = con.execute("SELECT COUNT(*) FROM usuarios WHERE rol='ADMIN' AND activo=1").fetchone()[0]
                if active_admins <= 1:
                    raise ValueError("No se puede desactivar al único administrador activo.")
            con.execute("UPDATE usuarios SET activo=? WHERE id=?", (1 if active else 0, user_id))
