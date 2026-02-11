"""
Аутентификация пользователей: хеширование паролей, проверка логина.
"""
import os
import hashlib
import logging
from typing import Optional, Dict, Any

from psycopg2.extras import RealDictCursor

from app.core.database import db_manager

logger = logging.getLogger(__name__)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Хеширует пароль PBKDF2-SHA256."""
    if salt is None:
        salt = os.urandom(16)
    iterations = 260_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Проверяет пароль по сохранённому хешу."""
    try:
        if stored_hash.startswith("pbkdf2_sha256$"):
            _, iterations_str, salt_hex, hash_hex = stored_hash.split("$", 3)
            iterations = int(iterations_str)
            salt = bytes.fromhex(salt_hex)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return dk.hex() == hash_hex
        # Fallback: plaintext (для миграции старых паролей)
        return password == stored_hash
    except Exception:
        logger.exception("Ошибка при проверке пароля")
        return False


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Проверяет логин/пароль в таблице app_users.
    Возвращает dict с данными пользователя или None.
    """
    with db_manager.connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, username, password_hash, is_active, full_name, role
                FROM app_users
                WHERE username = %s
                """,
                (username,),
            )
            row = cur.fetchone()

    if not row:
        logger.warning("Пользователь '%s' не найден", username)
        return None

    if not row["is_active"]:
        logger.warning("Пользователь '%s' деактивирован", username)
        return None

    if not verify_password(password, row["password_hash"]):
        logger.warning("Неверный пароль для '%s'", username)
        return None

    user = dict(row)
    user.pop("password_hash", None)
    logger.info("Успешная аутентификация: %s (id=%s)", username, user["id"])
    return user
