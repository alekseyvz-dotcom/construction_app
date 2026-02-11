"""
Диалоговые окна приложения.
"""
from app.dialogs.settings_dialog import SettingsDialog
from app.dialogs.user_dialogs import CreateUserDialog, EditUserDialog
from app.dialogs.permissions_dialog import PermissionsDialog

__all__ = [
    "SettingsDialog",
    "CreateUserDialog",
    "EditUserDialog",
    "PermissionsDialog",
]
