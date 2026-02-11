"""
Ядро приложения: БД, аутентификация, права, логирование.
"""
from app.core.database import db_manager, DatabaseManager
from app.core.auth import authenticate_user, hash_password, verify_password
from app.core.permissions import load_user_permissions, sync_permissions_from_menu_spec
from app.core.logging_config import setup_logging, get_app_dir

__all__ = [
    "db_manager",
    "DatabaseManager",
    "authenticate_user",
    "hash_password",
    "verify_password",
    "load_user_permissions",
    "sync_permissions_from_menu_spec",
    "setup_logging",
    "get_app_dir",
]
