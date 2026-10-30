from __future__ import annotations

import hashlib
import hmac
import os

ITERATIONS = 210_000


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return digest.hex(), salt.hex()


def verify_password(password: str, expected_hash: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return hmac.compare_digest(digest.hex(), expected_hash)
