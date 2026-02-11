"""
Главное окно приложения.
Кастомная навигационная панель, хедер, контент, футер.
"""
import logging
from typing import Dict, Any, Optional, Callable

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QMenu, QStackedWidget,
    QMessageBox, QStatusBar, QPushButton, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont

from app.core.permissions import load_user_permissions
from app.core.settings_manager import settings
from app.login_page import LoginPage
from app.home_page import HomePage
from app.dialogs.settings_dialog import SettingsDialog
from app.menu_spec import MENU_SPEC, TOP_LEVEL
from app.resources.styles import MAIN_STYLESHEET

logger = logging.getLogger(__name__)

APP_NAME = "Управление строительством"

PAGE_HEADERS: Dict[str, tuple] = {
    "home": ("Управление строительством", "Выберите раздел в меню навигации"),
    "login": ("Управление строительством", "Вход в систему"),
    "timesheet": ("Объектный табель", ""),
    "my_timesheets": ("Мои табели", ""),
    "timesheet_registry": ("Реестр табелей", ""),
    "workers": ("Работники", "Поиск по сотруднику и его объектам"),
    "timesheet_compare": ("Сравнение табелей", "Объектный vs Кадровый (1С)"),
    "transport": ("Заявка на спецтехнику", ""),
    "my_transport_orders": ("Мои заявки на транспорт", ""),
    "planning": ("Планирование транспорта", ""),
    "transport_registry": ("Реестр транспорта", ""),
    "meals_order": ("Заказ питания", ""),
    "my_meals_orders": ("Мои заявки на питание", ""),
    "meals_planning": ("Планирование питания", ""),
    "meals_registry": ("Реестр заявок на питание", ""),
    "meals_reports": ("Отчёты по питанию", "Дневной и месячный свод"),
    "meals_workers": ("Работники (питание)", "История питания"),
    "meals_settings": ("Настройки питания", ""),
    "lodging_registry": ("Проживание", "Реестр заселений/выселений"),
    "lodging_dorms": ("Проживание", "Общежития и комнаты"),
    "lodging_rates": ("Проживание", "Тарифы (цена за сутки)"),
    "object_create": ("Объекты: Создание/Редактирование", ""),
    "objects_registry": ("Реестр объектов", ""),
    "employee_card": ("Сотрудники", "Карточка сотрудника"),
    "budget": ("Анализ смет", ""),
    "analytics_dashboard": ("Операционная аналитика", "Сводные показатели"),
}

# Иконки-эмодзи для секций меню (можно заменить на QIcon)
SECTION_ICONS = {
    "Объектный табель": "📋",
    "Автотранспорт": "🚛",
    "Питание": "🍽",
    "Проживание": "🏠",
    "Объекты": "🏗",
    "Сотрудники": "👤",
    "Аналитика": "📊",
    "Инструменты": "🔧",
}


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(980, 640)
        self.resize(1100, 768)
        self.setStyleSheet(MAIN_STYLESHEET)

        # === Атрибуты ===
        self.current_user: Dict[str, Any] = {}
        self.is_authenticated: bool = False
        self._page_builders: Dict[str, Callable] = {}
        self._page_headers: Dict[str, tuple] = dict(PAGE_HEADERS)
        self._pages_cache: Dict[str, QWidget] = {}
        self._navigating: bool = False

        # Для управления правами: section_label -> (QPushButton, QMenu)
        self._nav_buttons: Dict[str, QPushButton] = {}
        self._nav_menus: Dict[str, QMenu] = {}
        self._menu_actions: Dict[str, QAction] = {}
        self._settings_btn: Optional[QPushButton] = None
        self._logout_btn: Optional[QPushButton] = None

        # === Убираем стандартный menubar ===
        self.menuBar().setVisible(False)

        # === Строим UI ===
        self._build_central_widget()
        self._build_statusbar()

        # === Показываем логин ===
        self.show_login()

    # ═══════════════════════════════════════════════════════════════
    #  ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ═══════════════════════════════════════════════════════════════

    def _build_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Навбар ───────────────────────────────────────────────
        self.navbar = self._build_navbar()
        main_layout.addWidget(self.navbar)

        # ── Хедер ────────────────────────────────────────────────
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e0e0e0;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 12, 20, 12)

        self.lbl_title = QLabel("")
        self.lbl_title.setObjectName("PageTitle")
        self.lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(self.lbl_title)

        header_layout.addStretch()

        self.lbl_hint = QLabel("")
        self.lbl_hint.setObjectName("PageHint")
        header_layout.addWidget(self.lbl_hint)

        main_layout.addWidget(header_widget)

        # ── Контент ──────────────────────────────────────────────
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentArea")
        main_layout.addWidget(self.content_stack, 1)

        # ── Футер ────────────────────────────────────────────────
        footer = QLabel("Разработал Алексей Зезюкин, 2025")
        footer.setObjectName("Footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer.setContentsMargins(16, 4, 16, 8)
        main_layout.addWidget(footer)

    def _build_navbar(self) -> QWidget:
        """Строит кастомную навигационную панель."""
        navbar = QWidget()
        navbar.setObjectName("NavBar")
        navbar.setFixedHeight(48)

        layout = QHBoxLayout(navbar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        # Название приложения
        app_title = QLabel("⚙ СтройУправление")
        app_title.setObjectName("NavAppTitle")
        layout.addWidget(app_title)

        # Разделитель
        layout.addWidget(self._make_separator())

        # Кнопка «Главная»
        btn_home = QPushButton("🏠 Главная")
        btn_home.setObjectName("NavHomeButton")
        btn_home.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_home.clicked.connect(self.show_home)
        layout.addWidget(btn_home)

        # Разделитель
        layout.addWidget(self._make_separator())

        # Кнопки-секции из MENU_SPEC
        for section in MENU_SPEC:
            icon = SECTION_ICONS.get(section.label, "")
            btn_text = f"{icon} {section.label}" if icon else section.label

            btn = QPushButton(btn_text)
            btn.setObjectName("NavButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # Создаём выпадающее меню
            menu = QMenu(btn)
            for entry in section.entries:
                if entry.kind == "separator":
                    menu.addSeparator()
                    continue
                if entry.kind == "page" and entry.key:
                    action = menu.addAction(entry.label)
                    action.setData(entry.key)
                    key = entry.key
                    action.triggered.connect(
                        lambda checked=False, k=key: self._navigate_to(k)
                    )
                    self._menu_actions[entry.key] = action

            btn.setMenu(menu)
            layout.addWidget(btn)

            self._nav_buttons[section.label] = btn
            self._nav_menus[section.label] = menu

        # Растягиваем пространство
        layout.addStretch()

        # Лейбл пользователя
        self.nav_user_label = QLabel("")
        self.nav_user_label.setObjectName("NavUserLabel")
        layout.addWidget(self.nav_user_label)

        # Разделитель
        layout.addWidget(self._make_separator())

        # Настройки
        self._settings_btn = QPushButton("⚙ Настройки")
        self._settings_btn.setObjectName("NavSettingsButton")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        # Выход
        self._logout_btn = QPushButton("🚪 Выход")
        self._logout_btn.setObjectName("NavSettingsButton")
        self._logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._logout_btn.clicked.connect(self._on_logout)
        layout.addWidget(self._logout_btn)

        return navbar

    @staticmethod
    def _make_separator() -> QFrame:
        """Создаёт вертикальный разделитель."""
        sep = QFrame()
        sep.setObjectName("NavSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        return sep

    def _build_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_user_status = QLabel("Не авторизован")
        self.status_bar.addPermanentWidget(self.lbl_user_status)

    # ═══════════════════════════════════════════════════════════════
    #  РЕГИСТРАЦИЯ СТРАНИЦ
    # ═══════════════════════════════════════════════════════════════

    def register_page(
        self,
        key: str,
        builder: Callable[["MainWindow"], QWidget],
        title: str = "",
        hint: str = "",
    ):
        self._page_builders[key] = builder
        if title:
            self._page_headers[key] = (title, hint)
        logger.debug("Зарегистрирована страница: %s", key)

    def register_pages(self, pages: Dict[str, Callable]):
        for key, builder in pages.items():
            self.register_page(key, builder)

    # ═══════════════════════════════════════════════════════════════
    #  НАВИГАЦИЯ
    # ═══════════════════════════════════════════════════════════════

    def _navigate_to(self, key: str):
        if self._navigating:
            return
        self._navigating = True
        try:
            self._do_navigate(key)
        finally:
            self._navigating = False

    def _do_navigate(self, key: str):
        if not self.is_authenticated and key != "login":
            self._do_navigate("login")
            return

        required_perm = self._perm_for_key(key)
        if (
            key not in ("login", "home")
            and required_perm
            and not self.has_perm(required_perm)
        ):
            QMessageBox.warning(
                self, "Доступ запрещён",
                "У вас нет прав на этот раздел.",
            )
            self._do_navigate("home")
            return

        title, hint = self._page_headers.get(
            key, (key.replace("_", " ").title(), "")
        )
        self._set_header(title, hint)

        try:
            page = self._create_page(key)
        except Exception as e:
            logger.exception("Ошибка при открытии страницы '%s'", key)
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось открыть страницу '{key}':\n{e}",
            )
            return

        if page is None:
            return

        idx = self.content_stack.indexOf(page)
        if idx < 0:
            idx = self.content_stack.addWidget(page)
        self.content_stack.setCurrentIndex(idx)

        # Скрываем/показываем навбар
        is_login = (key == "login")
        self.navbar.setVisible(not is_login)

    def _create_page(self, key: str) -> Optional[QWidget]:
        old = self._pages_cache.pop(key, None)
        if old is not None:
            idx = self.content_stack.indexOf(old)
            if idx >= 0:
                self.content_stack.removeWidget(old)
            old.deleteLater()

        if key == "login":
            page = LoginPage()
            page.login_successful.connect(self.on_login_success)
            page.exit_requested.connect(self.close)
        elif key == "home":
            logo_b64 = self._get_logo_base64()
            page = HomePage(logo_base64=logo_b64)
        else:
            builder = self._page_builders.get(key)
            if builder is None:
                raise RuntimeError(
                    f"Страница '{key}' не зарегистрирована. "
                    f"Используйте register_page()."
                )
            page = builder(self)

        self._pages_cache[key] = page
        return page

    def show_home(self):
        self._navigate_to("home")

    def show_login(self):
        self._set_user(None)
        self._navigate_to("login")

    # ═══════════════════════════════════════════════════════════════
    #  АУТЕНТИФИКАЦИЯ И ПРАВА
    # ═══════════════════════════════════════════════════════════════

    def on_login_success(self, user: Dict[str, Any]):
        logger.info("Успешный вход: %s", user.get("username"))
        try:
            user["permissions"] = load_user_permissions(user["id"])
        except Exception as e:
            logger.exception("Не удалось загрузить права")
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось загрузить права:\n{e}",
            )
            return
        self._set_user(user)
        self.show_home()

    def _set_user(self, user: Optional[Dict[str, Any]]):
        self.current_user = user or {}
        self.is_authenticated = bool(user)

        if user:
            name = user.get("full_name") or user.get("username", "")
            self.setWindowTitle(f"{APP_NAME} — {name}")
            self.lbl_user_status.setText(f"Пользователь: {name}")
            self.nav_user_label.setText(f"👤 {name}")
        else:
            self.setWindowTitle(APP_NAME)
            self.lbl_user_status.setText("Не авторизован")
            self.nav_user_label.setText("")

        self._apply_permissions()

    def has_perm(self, perm_code: str) -> bool:
        perms = self.current_user.get("permissions")
        return bool(perms and perm_code in perms)

    def _perm_for_key(self, key: str) -> Optional[str]:
        for section in MENU_SPEC:
            for entry in section.entries:
                if entry.kind == "page" and entry.key == key:
                    return entry.perm
        return None

    def _apply_permissions(self):
        """Включает/выключает кнопки и пункты меню по правам."""
        for section in MENU_SPEC:
            menu = self._nav_menus.get(section.label)
            btn = self._nav_buttons.get(section.label)

            any_enabled = False

            for entry in section.entries:
                if entry.kind != "page" or not entry.key:
                    continue

                action = self._menu_actions.get(entry.key)
                if not action:
                    continue

                if not entry.perm:
                    allowed = True
                else:
                    allowed = self.has_perm(entry.perm)

                action.setEnabled(allowed)
                if allowed:
                    any_enabled = True

            # Кнопка секции целиком
            if btn:
                btn.setEnabled(any_enabled)
                btn.setVisible(any_enabled and self.is_authenticated)

        # Настройки
        if self._settings_btn:
            settings_allowed = True
            for entry in TOP_LEVEL:
                if entry.perm:
                    settings_allowed = self.has_perm(entry.perm)
                    break
            self._settings_btn.setEnabled(settings_allowed)
            self._settings_btn.setVisible(self.is_authenticated)

        # Выход
        if self._logout_btn:
            self._logout_btn.setVisible(self.is_authenticated)

    def _on_logout(self):
        """Обработчик кнопки Выход."""
        answer = QMessageBox.question(
            self,
            "Выход",
            "Вы уверены, что хотите выйти из системы?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.show_login()

    # ═══════════════════════════════════════════════════════════════
    #  НАСТРОЙКИ
    # ═══════════════════════════════════════════════════════════════

    def _open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    # ═══════════════════════════════════════════════════════════════
    #  ВСПОМОГАТЕЛЬНЫЕ
    # ═══════════════════════════════════════════════════════════════

    def _set_header(self, title: str, hint: str = ""):
        self.lbl_title.setText(title)
        self.lbl_hint.setText(hint or "")

    @staticmethod
    def _get_logo_base64() -> Optional[str]:
        try:
            from app.resources.logo import LOGO_BASE64
            return LOGO_BASE64
        except (ImportError, AttributeError):
            return None

    def closeEvent(self, event):
        logger.info("Закрытие приложения...")
        from app.core.database import db_manager
        db_manager.close()
        event.accept()
