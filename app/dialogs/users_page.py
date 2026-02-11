"""
Страница управления пользователями (список + CRUD).
"""
import logging
from typing import Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView,
)
from PySide6.QtCore import Qt

from app.core.user_management import (
    get_app_users,
    create_app_user,
    update_app_user,
    delete_app_user,
    grant_default_permissions,
)
from app.dialogs.user_dialogs import CreateUserDialog, EditUserDialog
from app.dialogs.permissions_dialog import PermissionsDialog

logger = logging.getLogger(__name__)


# Колонки таблицы
_COLUMNS = [
    ("ID", 50),
    ("Логин", 130),
    ("ФИО", 220),
    ("Роль", 100),
    ("Подразделение", 180),
    ("Активен", 75),
]


class UsersPage(QWidget):
    """Виджет-страница для управления пользователями."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()
        self.reload_users()

    # ── Построение интерфейса ────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Кнопки
        toolbar = QHBoxLayout()

        btn_create = QPushButton("Создать пользователя")
        btn_create.clicked.connect(self._on_create)
        toolbar.addWidget(btn_create)

        btn_perms = QPushButton("Права...")
        btn_perms.setObjectName("SecondaryButton")
        btn_perms.clicked.connect(self._on_permissions)
        toolbar.addWidget(btn_perms)

        btn_edit = QPushButton("Изменить")
        btn_edit.setObjectName("SecondaryButton")
        btn_edit.clicked.connect(self._on_edit)
        toolbar.addWidget(btn_edit)

        btn_delete = QPushButton("Удалить")
        btn_delete.setObjectName("DangerButton")
        btn_delete.clicked.connect(self._on_delete)
        toolbar.addWidget(btn_delete)

        toolbar.addStretch()

        btn_refresh = QPushButton("Обновить")
        btn_refresh.setObjectName("SecondaryButton")
        btn_refresh.clicked.connect(self.reload_users)
        toolbar.addWidget(btn_refresh)

        layout.addLayout(toolbar)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([c[0] for c in _COLUMNS])
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        for i, (_, width) in enumerate(_COLUMNS):
            self.table.setColumnWidth(i, width)
        header.setStretchLastSection(True)

        # Двойной клик — редактирование
        self.table.doubleClicked.connect(self._on_edit)

        layout.addWidget(self.table)

    # ── Данные ───────────────────────────────────────────────────

    def reload_users(self):
        """Перезагружает список пользователей из БД."""
        self.table.setRowCount(0)

        try:
            users = get_app_users()
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось загрузить список пользователей:\n{e}",
            )
            return

        self._users_data = users
        self.table.setRowCount(len(users))

        for row, user in enumerate(users):
            items = [
                str(user["id"]),
                user["username"],
                user.get("full_name") or "",
                user.get("role") or "",
                user.get("department_name") or "",
                "Да" if user.get("is_active") else "Нет",
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col in (0, 5):  # ID и Активен — по центру
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)

    def _get_selected_user(self) -> Optional[Dict]:
        """Возвращает dict выбранного пользователя или None."""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(
                self, "Пользователи",
                "Выберите пользователя в таблице.",
            )
            return None

        if row >= len(self._users_data):
            return None

        return self._users_data[row]

    # ── Обработчики кнопок ───────────────────────────────────────

    def _on_create(self):
        dlg = CreateUserDialog(self)
        if dlg.exec() != CreateUserDialog.DialogCode.Accepted:
            return
        if not dlg.result_data:
            return

        data = dlg.result_data
        try:
            new_id = create_app_user(
                username=data["username"],
                password=data["password"],
                full_name=data["full_name"],
                role_code=data["role"],
                is_active=True,
                department_id=data.get("department_id"),
            )
            grant_default_permissions(new_id)
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось создать пользователя:\n{e}",
            )
            return

        self.reload_users()

        # Сразу открываем редактор прав
        perms_dlg = PermissionsDialog(
            user_id=new_id,
            username=data["username"],
            parent=self,
        )
        perms_dlg.exec()

    def _on_edit(self):
        user = self._get_selected_user()
        if not user:
            return

        dlg = EditUserDialog(user, self)
        if dlg.exec() != EditUserDialog.DialogCode.Accepted:
            return
        if not dlg.result_data:
            return

        data = dlg.result_data
        try:
            update_app_user(
                user_id=data["id"],
                username=data["username"],
                full_name=data["full_name"],
                role_code=data["role"],
                is_active=data["is_active"],
                new_password=data.get("password"),
                department_id=data.get("department_id"),
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось сохранить изменения:\n{e}",
            )
            return

        self.reload_users()
        QMessageBox.information(
            self, "Пользователи", "Изменения сохранены.",
        )

    def _on_delete(self):
        user = self._get_selected_user()
        if not user:
            return

        answer = QMessageBox.question(
            self, "Удалить пользователя",
            f"Удалить пользователя '{user['username']}'?\n"
            f"Это действие необратимо.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_app_user(user["id"])
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось удалить пользователя:\n{e}",
            )
            return

        self.reload_users()
        QMessageBox.information(
            self, "Пользователи", "Пользователь удалён.",
        )

    def _on_permissions(self):
        user = self._get_selected_user()
        if not user:
            return

        dlg = PermissionsDialog(
            user_id=user["id"],
            username=user["username"],
            parent=self,
        )
        dlg.exec()
