"""
Управление правами доступа пользователей.
"""
import logging
from typing import Set

from app.core.database import db_manager

logger = logging.getLogger(__name__)


def load_user_permissions(user_id: int) -> Set[str]:
    """Загружает набор разрешений пользователя из БД."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT perm_code FROM public.app_user_permissions WHERE user_id = %s",
                (user_id,),
            )
            perms = {row[0] for row in cur.fetchall()}

    logger.debug("Права пользователя id=%s: %s", user_id, perms)
    return perms


def sync_permissions_from_menu_spec() -> None:
    """
    Синхронизирует таблицу app_permissions из menu_spec.
    Вызывается один раз при старте приложения.
    """
    from app.menu_spec import MENU_SPEC, TOP_LEVEL

    rows = {}
    for section in MENU_SPEC:
        for entry in section.entries:
            if entry.perm:
                rows[entry.perm] = (
                    entry.perm,
                    entry.title or entry.perm,
                    entry.group or "core",
                )

    for entry in TOP_LEVEL:
        if entry.perm:
            rows[entry.perm] = (
                entry.perm,
                entry.title or entry.perm,
                entry.group or "core",
            )

    if not rows:
        return

    values = list(rows.values())

    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO public.app_permissions (code, title, group_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (code) DO UPDATE
                    SET title = EXCLUDED.title,
                        group_name = EXCLUDED.group_name
                """,
                values,
            )
        conn.commit()

    logger.info("Синхронизировано %d разрешений из menu_spec", len(values))
