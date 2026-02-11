"""
Диалоги создания и редактирования пользователей.
"""
import logging
from typing import Optional, Dict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

from app.core.user_management import (
    get_roles_list,
    get_departments_list,
)

logger = logging.getLogger(__name__)


class CreateUserDialog(QDialog):
    """Диалог создания нового пользователя."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать пользователя")
        self.setMinimumWidth(420)
        self.result_data: Optional[Dict] = None

        self._load_reference_data()
        self._build_ui()

    def _load_reference_data(self):
        """Загружает роли и подразделения из БД."""
        try:
            roles = get_roles_list()
        except Exception as e:
            logger.exception("Ошибка загрузки ролей")
            roles = []

        try:
            departments = get_departments_list()
        except Exception as e:
            logger.exception("Ошибка загрузки подразделений")
            departments = []

        # role_display -> role_code
        self._role_map: Dict[str, str] = {
            f'{r["name"]} ({r["code"]})': r["code"] for r in roles
        }
        # dep_display -> dep_id (None для "нет")
        self._dep_map: Dict[str, Optional[int]] = {"(нет)": None}
        for d in departments:
            self._dep_map[d["name"]] = d["id"]

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Форма
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(1, 240)

        # Логин
        grid.addWidget(QLabel("Логин:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Введите логин")
        grid.addWidget(self.input_username, 0, 1)

        # ФИО
        grid.addWidget(QLabel("ФИО:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self.input_fullname = QLineEdit()
        self.input_fullname.setPlaceholderText("Полное имя")
        grid.addWidget(self.input_fullname, 1, 1)

        # Пароль
        grid.addWidget(QLabel("Пароль:"), 2, 0, Qt.AlignmentFlag.AlignRight)
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setPlaceholderText("Введите пароль")
        grid.addWidget(self.input_password, 2, 1)

        # Роль
        grid.addWidget(QLabel("Роль:"), 3, 0, Qt.AlignmentFlag.AlignRight)
        self.combo_role = QComboBox()
        self.combo_role.addItems(list(self._role_map.keys()))
        grid.addWidget(self.combo_role, 3, 1)

        # Подразделение
        grid.addWidget(
            QLabel("Подразделение:"), 4, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.combo_department = QComboBox()
        self.combo_department.addItems(list(self._dep_map.keys()))
        grid.addWidget(self.combo_department, 4, 1)

        layout.addLayout(grid)
        layout.addSpacing(16)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_ok = QPushButton("Создать")
        btn_ok.clicked.connect(self._on_accept)
        btn_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _on_accept(self):
        username = self.input_username.text().strip()
        password = self.input_password.text().strip()

        if not username:
            QMessageBox.warning(self, "Создать", "Укажите логин.")
            self.input_username.setFocus()
            return
        if not password:
            QMessageBox.warning(self, "Создать", "Укажите пароль.")
            self.input_password.setFocus()
            return
        if not self.combo_role.currentText():
            QMessageBox.warning(self, "Создать", "Выберите роль.")
            return

        role_display = self.combo_role.currentText()
        dep_display = self.combo_department.currentText()

        self.result_data = {
            "username": username,
            "full_name": self.input_fullname.text().strip(),
            "password": password,
            "role": self._role_map[role_display],
            "department_id": self._dep_map.get(dep_display),
        }
        self.accept()


class EditUserDialog(QDialog):
    """Диалог редактирования существующего пользователя."""

    def __init__(self, user: Dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            f"Редактировать: {user.get('username', '')}"
        )
        self.setMinimumWidth(420)
        self.user = user
        self.result_data: Optional[Dict] = None

        self._load_reference_data()
        self._build_ui()
        self._populate_fields()

    def _load_reference_data(self):
        try:
            roles = get_roles_list()
        except Exception:
            roles = []

        try:
            departments = get_departments_list()
        except Exception:
            departments = []

        self._role_map: Dict[str, str] = {
            f'{r["name"]} ({r["code"]})': r["code"] for r in roles
        }
        self._dep_map: Dict[str, Optional[int]] = {"(нет)": None}
        for d in departments:
            self._dep_map[d["name"]] = d["id"]

    def _build_ui(self):
        layout = QVBoxLayout(self)

        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(1, 240)

        # Логин
        grid.addWidget(QLabel("Логин:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.input_username = QLineEdit()
        grid.addWidget(self.input_username, 0, 1)

        # ФИО
        grid.addWidget(QLabel("ФИО:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self.input_fullname = QLineEdit()
        grid.addWidget(self.input_fullname, 1, 1)

        # Пароль
        grid.addWidget(
            QLabel("Новый пароль:"), 2, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_password.setPlaceholderText("Оставьте пустым, чтобы не менять")
        grid.addWidget(self.input_password, 2, 1)

        # Роль
        grid.addWidget(QLabel("Роль:"), 3, 0, Qt.AlignmentFlag.AlignRight)
        self.combo_role = QComboBox()
        self.combo_role.addItems(list(self._role_map.keys()))
        grid.addWidget(self.combo_role, 3, 1)

        # Подразделение
        grid.addWidget(
            QLabel("Подразделение:"), 4, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.combo_department = QComboBox()
        self.combo_department.addItems(list(self._dep_map.keys()))
        grid.addWidget(self.combo_department, 4, 1)

        # Активен
        grid.addWidget(
            QLabel("Активен:"), 5, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.check_active = QCheckBox()
        grid.addWidget(self.check_active, 5, 1)

        layout.addLayout(grid)
        layout.addSpacing(16)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_ok = QPushButton("Сохранить")
        btn_ok.clicked.connect(self._on_accept)
        btn_layout.addWidget(btn_ok)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def _populate_fields(self):
        """Заполняет поля данными пользователя."""
        self.input_username.setText(self.user.get("username", ""))
        self.input_fullname.setText(self.user.get("full_name") or "")
        self.check_active.setChecked(bool(self.user.get("is_active")))

        # Роль
        current_role = (self.user.get("role") or "").lower()
        for i, (display, code) in enumerate(self._role_map.items()):
            if code.lower() == current_role:
                self.combo_role.setCurrentIndex(i)
                break

        # Подразделение
        current_dep = self.user.get("department_name")
        if current_dep and current_dep in self._dep_map:
            idx = list(self._dep_map.keys()).index(current_dep)
            self.combo_department.setCurrentIndex(idx)
        else:
            self.combo_department.setCurrentIndex(0)  # "(нет)"

    def _on_accept(self):
        username = self.input_username.text().strip()
        if not username:
            QMessageBox.warning(self, "Редактировать", "Укажите логин.")
            self.input_username.setFocus()
            return
        if not self.combo_role.currentText():
            QMessageBox.warning(self, "Редактировать", "Выберите роль.")
            return

        role_display = self.combo_role.currentText()
        dep_display = self.combo_department.currentText()

        self.result_data = {
            "id": self.user["id"],
            "username": username,
            "full_name": self.input_fullname.text().strip(),
            "password": self.input_password.text().strip() or None,
            "role": self._role_map[role_display],
            "is_active": self.check_active.isChecked(),
            "department_id": self._dep_map.get(dep_display),
        }
        self.accept()
