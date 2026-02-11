"""
Управление пользователями приложения.
CRUD операции, роли, подразделения — без GUI.
"""
import os
import hashlib
import logging
from typing import Dict, List, Optional, Any

from psycopg2.extras import RealDictCursor

from app.core.database import db_manager

logger = logging.getLogger(__name__)


# ─── Хеширование паролей ────────────────────────────────────────────

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Хеширует пароль PBKDF2-SHA256."""
    if salt is None:
        salt = os.urandom(16)
    iterations = 260_000
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Проверяет пароль по хешу."""
    try:
        if stored_hash.startswith("pbkdf2_sha256$"):
            _, it_str, salt_hex, hash_hex = stored_hash.split("$", 3)
            salt = bytes.fromhex(salt_hex)
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, int(it_str),
            )
            return dk.hex() == hash_hex
        return password == stored_hash
    except Exception:
        logger.exception("Ошибка проверки пароля")
        return False


# ─── Подразделения ───────────────────────────────────────────────────

def get_departments_list() -> List[Dict]:
    """Список подразделений [{id, name}, ...]."""
    return db_manager.execute_query(
        "SELECT id, name FROM departments ORDER BY name"
    )


# ─── Роли ────────────────────────────────────────────────────────────

def get_roles_list() -> List[Dict]:
    """Список ролей [{code, name}, ...]."""
    return db_manager.execute_query(
        "SELECT code, name FROM roles ORDER BY name"
    )


# ─── Пользователи CRUD ──────────────────────────────────────────────

def get_app_users() -> List[Dict]:
    """Список всех пользователей с названием подразделения."""
    return db_manager.execute_query(
        """
        SELECT u.id, u.username, u.full_name, u."role",
               u.is_active, u.department_id,
               d.name AS department_name
        FROM app_users u
        LEFT JOIN departments d ON d.id = u.department_id
        ORDER BY u.username
        """
    )


def create_app_user(
    username: str,
    password: str,
    full_name: str,
    role_code: str,
    is_active: bool = True,
    department_id: Optional[int] = None,
) -> int:
    """
    Создаёт пользователя и возвращает его id.
    Raises ValueError при невалидных данных.
    """
    username = (username or "").strip()
    full_name = (full_name or "").strip()
    role_code = (role_code or "").strip().lower()

    if not username:
        raise ValueError("Логин не может быть пустым")
    if not password:
        raise ValueError("Пароль не может быть пустым")
    if not role_code:
        raise ValueError("Роль не указана")

    pwd_hash = hash_password(password)

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_users
                    (username, password_hash, is_active,
                     full_name, "role", department_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    username, pwd_hash, is_active,
                    full_name, role_code, department_id,
                ),
            )
            new_id = cur.fetchone()[0]
        conn.commit()

    logger.info("Создан пользователь '%s' (id=%d)", username, new_id)
    return new_id


def update_app_user(
    user_id: int,
    username: str,
    full_name: str,
    role_code: str,
    is_active: bool,
    new_password: Optional[str] = None,
    department_id: Optional[int] = None,
) -> None:
    """Обновляет данные пользователя."""
    username = (username or "").strip()
    full_name = (full_name or "").strip()
    role_code = (role_code or "").strip().lower()

    if not username:
        raise ValueError("Логин не может быть пустым")
    if not role_code:
        raise ValueError("Роль не указана")

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            if new_password:
                pwd_hash = hash_password(new_password)
                cur.execute(
                    """
                    UPDATE app_users
                    SET username = %s, full_name = %s, "role" = %s,
                        is_active = %s, password_hash = %s,
                        department_id = %s
                    WHERE id = %s
                    """,
                    (
                        username, full_name, role_code,
                        is_active, pwd_hash, department_id, user_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE app_users
                    SET username = %s, full_name = %s, "role" = %s,
                        is_active = %s, department_id = %s
                    WHERE id = %s
                    """,
                    (
                        username, full_name, role_code,
                        is_active, department_id, user_id,
                    ),
                )
        conn.commit()

    logger.info("Обновлён пользователь id=%d", user_id)


def delete_app_user(user_id: int) -> None:
    """Удаляет пользователя."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM app_users WHERE id = %s", (user_id,))
        conn.commit()

    logger.info("Удалён пользователь id=%d", user_id)


# ─── Права ───────────────────────────────────────────────────────────

def get_permissions_catalog() -> List[Dict]:
    """Справочник всех прав [{code, title, group_name}, ...]."""
    return db_manager.execute_query(
        """
        SELECT code, title, group_name
        FROM public.app_permissions
        ORDER BY group_name, title
        """
    )


def get_user_permissions(user_id: int) -> set:
    """Набор кодов прав пользователя."""
    rows = db_manager.execute_query(
        "SELECT perm_code FROM public.app_user_permissions WHERE user_id = %s",
        (user_id,),
    )
    return {r["perm_code"] for r in rows}


def set_user_permissions(user_id: int, perm_codes: List[str]) -> None:
    """Полная перезапись прав пользователя."""
    perm_codes = sorted({
        p.strip() for p in perm_codes if p and p.strip()
    })

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM public.app_user_permissions WHERE user_id = %s",
                (user_id,),
            )
            if perm_codes:
                cur.executemany(
                    """
                    INSERT INTO public.app_user_permissions (user_id, perm_code)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    [(user_id, p) for p in perm_codes],
                )
        conn.commit()

    logger.info(
        "Обновлены права пользователя id=%d: %d прав", user_id, len(perm_codes),
    )


def grant_default_permissions(user_id: int) -> None:
    """Выдаёт минимальные права новому пользователю."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.app_user_permissions (user_id, perm_code)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (user_id, "page.home"),
            )
        conn.commit()
