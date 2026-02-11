"""
Окно настроек приложения.
Вкладки: Папки, Основное, База данных, Пользователи, Данные (импорт).
"""
import logging
from pathlib import Path
from typing import Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QTabWidget, QWidget, QLabel, QLineEdit, QComboBox,
    QPushButton, QFileDialog, QMessageBox, QGroupBox,
)
from PySide6.QtCore import Qt

from app.core.settings_manager import settings, Keys, DEFAULTS
from app.core.excel_import import (
    import_employees_from_excel,
    import_objects_from_excel,
)
from app.pages.users_page import UsersPage

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Главное окно настроек приложения."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumSize(760, 560)
        self.resize(820, 600)

        # Словарь для хранения виджетов ввода: section -> key -> widget
        self._inputs: Dict[str, Dict[str, Any]] = {}

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._build_paths_tab()
        self._build_general_tab()
        self._build_db_tab()
        self._build_users_tab()
        self._build_data_tab()

        # Кнопки внизу
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    # ── Вкладка: Настройки папок ─────────────────────────────────

    def _build_paths_tab(self):
        tab = QWidget()
        grid = QGridLayout(tab)
        grid.setSpacing(10)
        grid.setContentsMargins(16, 16, 16, 16)

        self._add_path_row(
            grid, 0, "Справочник (xlsx):",
            "Paths", Keys.SPR, is_dir=False,
        )
        self._add_path_row(
            grid, 1, "Папка табелей:",
            "Paths", Keys.OUTPUT_DIR, is_dir=True,
        )
        self._add_path_row(
            grid, 2, "Папка заявок на питание:",
            "Paths", Keys.MEALS_ORDERS_DIR, is_dir=True,
        )

        grid.setRowStretch(10, 1)
        self.tabs.addTab(tab, "Папки")

    # ── Вкладка: Основное ────────────────────────────────────────

    def _build_general_tab(self):
        tab = QWidget()
        grid = QGridLayout(tab)
        grid.setSpacing(10)
        grid.setContentsMargins(16, 16, 16, 16)

        self._add_text_row(
            grid, 0, "Подразделение по умолчанию:",
            "UI", Keys.SELECTED_DEP, width=300,
        )
        self._add_text_row(
            grid, 1, "Подразделения водителей:",
            "Integrations", Keys.DRIVER_DEPARTMENTS, width=450,
        )

        grid.setRowStretch(10, 1)
        self.tabs.addTab(tab, "Основное")

    # ── Вкладка: База данных ─────────────────────────────────────

    def _build_db_tab(self):
        tab = QWidget()
        grid = QGridLayout(tab)
        grid.setSpacing(10)
        grid.setContentsMargins(16, 16, 16, 16)

        # Провайдер
        grid.addWidget(
            QLabel("Провайдер:"), 0, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["sqlite", "postgres", "mysql"])
        current = settings.get("DB", "provider")
        idx = self.combo_provider.findText(current)
        if idx >= 0:
            self.combo_provider.setCurrentIndex(idx)
        self.combo_provider.currentTextChanged.connect(
            self._on_provider_changed
        )
        grid.addWidget(self.combo_provider, 0, 1)
        self._register_input("DB", "provider", self.combo_provider)

        # DATABASE_URL
        grid.addWidget(
            QLabel("Строка подключения\n(DATABASE_URL):"),
            1, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.input_db_url = QLineEdit()
        self.input_db_url.setText(settings.get("DB", "database_url"))
        self.input_db_url.setMinimumWidth(450)
        grid.addWidget(self.input_db_url, 1, 1, 1, 2)
        self._register_input("DB", "database_url", self.input_db_url)

        # SQLite путь
        grid.addWidget(
            QLabel("SQLite файл:"), 2, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.input_sqlite = QLineEdit()
        self.input_sqlite.setText(settings.get("DB", "sqlite_path"))
        grid.addWidget(self.input_sqlite, 2, 1)

        btn_browse_sqlite = QPushButton("...")
        btn_browse_sqlite.setMaximumWidth(40)
        btn_browse_sqlite.clicked.connect(self._browse_sqlite)
        grid.addWidget(btn_browse_sqlite, 2, 2)
        self._register_input("DB", "sqlite_path", self.input_sqlite)

        # SSL mode
        grid.addWidget(
            QLabel("SSL mode (Postgres):"),
            3, 0, Qt.AlignmentFlag.AlignRight,
        )
        self.combo_ssl = QComboBox()
        self.combo_ssl.addItems([
            "require", "verify-full", "prefer", "disable",
        ])
        current_ssl = settings.get("DB", "sslmode")
        idx = self.combo_ssl.findText(current_ssl)
        if idx >= 0:
            self.combo_ssl.setCurrentIndex(idx)
        grid.addWidget(self.combo_ssl, 3, 1)
        self._register_input("DB", "sslmode", self.combo_ssl)

        grid.setRowStretch(10, 1)
        self.tabs.addTab(tab, "База данных")

        # Применяем начальное состояние полей
        self._on_provider_changed(self.combo_provider.currentText())

    def _on_provider_changed(self, provider: str):
        """Включает/выключает поля в зависимости от провайдера."""
        is_sqlite = (provider == "sqlite")
        self.input_db_url.setEnabled(not is_sqlite)
        self.input_sqlite.setEnabled(is_sqlite)
        self.combo_ssl.setEnabled(not is_sqlite)

    def _browse_sqlite(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Файл SQLite", "",
            "SQLite DB (*.sqlite3 *.db);;Все файлы (*.*)",
        )
        if path:
            self.input_sqlite.setText(path)

    # ── Вкладка: Пользователи ───────────────────────────────────

    def _build_users_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        self.users_page = UsersPage(tab)
        layout.addWidget(self.users_page)

        self.tabs.addTab(tab, "Пользователи")

    # ── Вкладка: Данные (импорт) ────────────────────────────────

    def _build_data_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)

        # === Импорт сотрудников ===
        group_emp = QGroupBox("Импорт сотрудников из Excel")
        emp_layout = QVBoxLayout(group_emp)

        emp_layout.addWidget(QLabel(
            "Ожидается файл штатного расписания с колонками:\n"
            "• Табельный номер (с префиксами)\n"
            "• Сотрудник\n"
            "• Должность\n"
            "• Подразделение\n"
            "• Дата увольнения"
        ))

        btn_import_emp = QPushButton("Загрузить сотрудников из Excel...")
        btn_import_emp.setMaximumWidth(300)
        btn_import_emp.clicked.connect(self._on_import_employees)
        emp_layout.addWidget(btn_import_emp)

        layout.addWidget(group_emp)

        # === Импорт объектов ===
        group_obj = QGroupBox("Импорт объектов из Excel")
        obj_layout = QVBoxLayout(group_obj)

        obj_layout.addWidget(QLabel(
            "Ожидается файл «Справочник программ и объектов» с колонками:\n"
            "• ID (код) номер объекта\n"
            "• Год, Программа, Заказчик, Адрес\n"
            "• № договора, Дата договора\n"
            "• Сокращённое наименование, Подразделение, Тип договора"
        ))

        btn_import_obj = QPushButton("Загрузить объекты из Excel...")
        btn_import_obj.setMaximumWidth(300)
        btn_import_obj.clicked.connect(self._on_import_objects)
        obj_layout.addWidget(btn_import_obj)

        layout.addWidget(group_obj)
        layout.addStretch()

        self.tabs.addTab(tab, "Данные")

    def _on_import_employees(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл штатного расписания", "",
            "Excel (*.xlsx *.xls);;Все файлы (*.*)",
        )
        if not path:
            return

        try:
            count = import_employees_from_excel(Path(path))
            QMessageBox.information(
                self, "Импорт сотрудников",
                f"Импорт завершён.\nОбработано записей: {count}",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка импорта",
                f"Ошибка при импорте сотрудников:\n{e}",
            )

    def _on_import_objects(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл справочника объектов", "",
            "Excel (*.xlsx *.xls);;Все файлы (*.*)",
        )
        if not path:
            return

        try:
            count = import_objects_from_excel(Path(path))
            QMessageBox.information(
                self, "Импорт объектов",
                f"Импорт завершён.\nОбработано записей: {count}",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка импорта",
                f"Ошибка при импорте объектов:\n{e}",
            )

    # ── Вспомогательные методы ───────────────────────────────────

    def _add_text_row(
        self, grid: QGridLayout, row: int, label: str,
        section: str, key: str, width: int = 300,
    ):
        """Добавляет строку: метка + текстовое поле."""
        grid.addWidget(
            QLabel(label), row, 0, Qt.AlignmentFlag.AlignRight,
        )
        inp = QLineEdit()
        inp.setText(settings.get(section, key))
        inp.setMinimumWidth(width)
        grid.addWidget(inp, row, 1, 1, 2)
        self._register_input(section, key, inp)

    def _add_path_row(
        self, grid: QGridLayout, row: int, label: str,
        section: str, key: str, is_dir: bool,
    ):
        """Добавляет строку: метка + путь + кнопка выбора."""
        grid.addWidget(
            QLabel(label), row, 0, Qt.AlignmentFlag.AlignRight,
        )
        inp = QLineEdit()
        inp.setText(settings.get(section, key))
        inp.setMinimumWidth(400)
        grid.addWidget(inp, row, 1)

        btn = QPushButton("...")
        btn.setMaximumWidth(40)
        btn.clicked.connect(
            lambda checked=False, w=inp, d=is_dir: self._browse_path(w, d)
        )
        grid.addWidget(btn, row, 2)
        self._register_input(section, key, inp)

    def _browse_path(self, widget: QLineEdit, is_dir: bool):
        if is_dir:
            path = QFileDialog.getExistingDirectory(
                self, "Выбор папки",
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Выбор файла", "",
                "Excel (*.xlsx *.xls);;Все файлы (*.*)",
            )
        if path:
            widget.setText(path)

    def _register_input(self, section: str, key: str, widget):
        """Регистрирует виджет ввода для последующего сохранения."""
        self._inputs.setdefault(section, {})[key] = widget

    # ── Сохранение ───────────────────────────────────────────────

    def _on_save(self):
        """Собирает значения из всех виджетов и сохраняет."""
        for section, keys in self._inputs.items():
            for key, widget in keys.items():
                if isinstance(widget, QComboBox):
                    value = widget.currentText()
                elif isinstance(widget, QLineEdit):
                    value = widget.text()
                else:
                    continue
                settings.set(section, key, value)

        settings.save()

        QMessageBox.information(
            self, "Настройки", "Настройки сохранены.",
        )
        self.accept()
