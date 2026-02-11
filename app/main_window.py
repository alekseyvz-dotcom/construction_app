"""
Главное окно приложения.
Содержит меню, хедер, контентную область и футер.
"""
import logging
from typing import Dict, Any, Optional, Callable

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QMenu, QStackedWidget,
    QMessageBox, QStatusBar,
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

# Заголовки страниц: key -> (title, hint)
PAGE_HEADERS: Dict[str, tuple] = {
    "home": ("Управление строительством", "Выберите раздел в верхнем меню"),
    "login": ("Управление строительством", "Вход в систему"),
    "timesheet": ("Объектный табель", ""),
    "my_timesheets": ("Мои табели", ""),
    "timesheet_registry": ("Реестр табелей", ""),
    "workers": ("Работники", "Поиск по сотруднику и его объектам"),
    "timesheet_compare": ("Сравнение табелей", "Объектный vs Кадровый (1С)"),
    "transport": ("Заявка на спецтехнику", ""),
    "my_transport_": ("Мои заявки на транспорт", ""),
    "planning": ("Планирование транспорта", ""),
    "transport_registry": ("Реестр транспорта", ""),
    "meals_order": ("Заказ питания", ""),
    "my_meals_orders": ("Мои заявки на питание", ""),
    "meals_planning": ("Планирование питания", ""),
    "meals_registry": ("Реестр заявок на питание", ""),
    "meals_reports": ("Отчёты по питанию", "Дневной и месячный свод по комплексам"),
    "meals_workers": ("Работники (питание)", "История питания по сотруднику"),
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


class MainWindow(QMainWindow):
    """
    Главное окно приложения.
    Управляет навигацией, аутентификацией, правами доступа.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(980, 640)
        self.resize(1100, 768)
        self.setStyleSheet(MAIN_STYLESHEET)

        self.current_user: Dict[str, Any] = {}
        self.is_authenticated: bool = False

        # key -> callable(main_window) -> QWidget
        self._page_builders: Dict[str, Callable] = {}
        # key -> (title, hint) — можно переопределять при регистрации
        self._page_headers: Dict[str, tuple] = dict(PAGE_HEADERS)
        # Реестр QAction для управления enabled/disabled
        self._menu_actions: Dict[str, QAction] = {}
        # Реестр QMenu секций
        self._section_menus: Dict[str, QMenu] = {}

        self._build_central_widget()
        self._build_menu()
        self._build_statusbar()

        # Показываем логин
        self.show_login()

    # ═══════════════════════════════════════════════════════════════
    #  ПОСТРОЕНИЕ ИНТЕРФЕЙСА
    # ═══════════════════════════════════════════════════════════════

    def _build_central_widget(self):
        """Создаёт центральный виджет: хедер + стек страниц + футер."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Хедер ────────────────────────────────────────────────
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 10, 16, 6)

        self.lbl_title = QLabel("")
        self.lbl_title.setObjectName("PageTitle")
        self.lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(self.lbl_title)

        header_layout.addStretch()

        self.lbl_hint = QLabel("")
        self.lbl_hint.setObjectName("PageHint")
        header_layout.addWidget(self.lbl_hint)

        main_layout.addWidget(header_widget)

        # ── Контент (стек) ───────────────────────────────────────
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentArea")
        main_layout.addWidget(self.content_stack, 1)

        # ── Футер ────────────────────────────────────────────────
        footer = QLabel("Разработал Алексей Зезюкин, 2025")
        footer.setObjectName("Footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer.setContentsMargins(16, 4, 16, 8)
        main_layout.addWidget(footer)

    def _build_statusbar(self):
        """Статусбар с информацией о пользователе."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_user_status = QLabel("Не авторизован")
        self.status_bar.addPermanentWidget(self.lbl_user_status)

    def _build_menu(self):
        """Строит меню из MENU_SPEC."""
        menubar = self.menuBar()

        # Главная — всегда доступна
        act_home = menubar.addAction("Главная")
        act_home.triggered.connect(self.show_home)

        # Секции из MENU_SPEC
        for section in MENU_SPEC:
            menu = menubar.addMenu(section.label)
            self._section_menus[section.label] = menu

            for entry in section.entries:
                if entry.kind == "separator":
                    menu.addSeparator()
                    continue

                if entry.kind == "page" and entry.key:
                    action = menu.addAction(entry.label)
                    action.setData(entry.key)

                    # Замыкание: привязка key через параметр по умолчанию
                    key = entry.key
                    action.triggered.connect(
                        lambda checked=False, k=key: self._navigate_to(k)
                    )
                    self._menu_actions[entry.key] = action

        # Настройки (top-level команда)
        act_settings = menubar.addAction("Настройки")
        act_settings.triggered.connect(self._open_settings)
        self._menu_actions["settings"] = act_settings

    # ═══════════════════════════════════════════════════════════════
    #  РЕГИСТРАЦИЯ СТРАНИЦ (для модулей)
    # ═══════════════════════════════════════════════════════════════

    def register_page(
        self,
        key: str,
        builder: Callable[["MainWindow"], QWidget],
        title: str = "",
        hint: str = "",
    ):
        """
        Регистрирует построитель страницы.

        Args:
            key: уникальный ключ страницы (совпадает с key в menu_spec)
            builder: функция(main_window) -> QWidget
            title: заголовок (если не задан, берётся из PAGE_HEADERS)
            hint: подсказка
        """
        self._page_builders[key] = builder
        if title:
            self._page_headers[key] = (title, hint)
        logger.debug("Зарегистрирована страница: %s", key)

    def register_pages(self, pages: Dict[str, Callable]):
        """
        Массовая регистрация страниц.
        pages: {key: builder_callable, ...}
        """
        for key, builder in pages.items():
            self.register_page(key, builder)

    # ═══════════════════════════════════════════════════════════════
    #  НАВИГАЦИЯ
    # ═══════════════════════════════════════════════════════════════

    def _navigate_to(self, key: str):
        """Переключает на страницу по ключу."""
        # Проверка аутентификации
        if not self.is_authenticated and key not in ("login",):
            self.show_login()
            return

        # Проверка прав
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
            self.show_home()
            return

        # Обновляем хедер
        title, hint = self._page_headers.get(
            key, (key.replace("_", " ").title(), "")
        )
        self._set_header(title, hint)

        # Создаём или получаем страницу
        try:
            page = self._get_or_create_page(key)
        except Exception as e:
            logger.exception("Ошибка при открытии страницы '%s'", key)
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось открыть страницу '{key}':\n{e}",
            )
            if self.is_authenticated:
                self.show_home()
            else:
                self.show_login()
            return

        # Показываем страницу
        idx = self.content_stack.indexOf(page)
        if idx < 0:
            idx = self.content_stack.addWidget(page)
        self.content_stack.setCurrentIndex(idx)

    def _get_or_create_page(self, key: str) -> QWidget:
        """
        Возвращает виджет страницы.
        Для login/home — всегда пересоздаёт.
        Для остальных — пересоздаёт при каждом переходе
        (чтобы данные были свежими).
        """
        # Удаляем старую страницу из стека, если есть
        old_page = self._pages_cache.get(key)
        if old_page is not None:
            idx = self.content_stack.indexOf(old_page)
            if idx >= 0:
                self.content_stack.removeWidget(old_page)
            old_page.deleteLater()
            del self._pages_cache[key]

        # Создаём новую
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
        """Переход на домашнюю страницу."""
        self._navigate_to("home")

    def show_login(self):
        """Переход на страницу логина."""
        self._set_user(None)
        self._navigate_to("login")

    # ═══════════════════════════════════════════════════════════════
    #  АУТЕНТИФИКАЦИЯ И ПРАВА
    # ═══════════════════════════════════════════════════════════════

    def on_login_success(self, user: Dict[str, Any]):
        """Вызывается после успешного входа."""
        logger.info("Успешный вход: %s", user.get("username"))

        # Загрузка прав
        try:
            user["permissions"] = load_user_permissions(user["id"])
        except Exception as e:
            logger.exception("Не удалось загрузить права")
            QMessageBox.critical(
                self, "Ошибка",
                f"Не удалось загрузить права пользователя:\n{e}",
            )
            return

        self._set_user(user)
        self.show_home()

    def _set_user(self, user: Optional[Dict[str, Any]]):
        """Устанавливает текущего пользователя и обновляет UI."""
        self.current_user = user or {}
        self.is_authenticated = bool(user)

        # Заголовок окна
        if user:
            name = user.get("full_name") or user.get("username", "")
            self.setWindowTitle(f"{APP_NAME} — {name}")
            self.lbl_user_status.setText(f"Пользователь: {name}")
        else:
            self.setWindowTitle(APP_NAME)
            self.lbl_user_status.setText("Не авторизован")

        # Обновить видимость пунктов меню
        self._apply_permissions()

    def has_perm(self, perm_code: str) -> bool:
        """Проверяет наличие права у текущего пользователя."""
        perms = self.current_user.get("permissions")
        return bool(perms and perm_code in perms)

    def _perm_for_key(self, key: str) -> Optional[str]:
        """Находит код права для страницы по ключу из MENU_SPEC."""
        for section in MENU_SPEC:
            for entry in section.entries:
                if entry.kind == "page" and entry.key == key:
                    return entry.perm
        return None

    def _apply_permissions(self):
        """Включает/выключает пункты меню по правам пользователя."""

        # Пункты внутри секций
        for section in MENU_SPEC:
            for entry in section.entries:
                if entry.kind != "page" or not entry.key:
                    continue

                action = self._menu_actions.get(entry.key)
                if not action:
                    continue

                if not entry.perm:
                    action.setEnabled(True)
                else:
                    action.setEnabled(self.has_perm(entry.perm))

        # Секции целиком: если нет ни одного доступного пункта — disable
        for section in MENU_SPEC:
            menu = self._section_menus.get(section.label)
            if not menu:
                continue

            any_enabled = any(
                (e.kind == "page")
                and ((not e.perm) or self.has_perm(e.perm))
                for e in section.entries
            )
            menu.setEnabled(any_enabled)

        # Top-level (Настройки и др.)
        for entry in TOP_LEVEL:
            if not entry.perm:
                continue
            action = self._menu_actions.get("settings")
            if action:
                action.setEnabled(self.has_perm(entry.perm))

    # ═══════════════════════════════════════════════════════════════
    #  НАСТРОЙКИ
    # ═══════════════════════════════════════════════════════════════

    def _open_settings(self):
        """Открывает окно настроек."""
        dlg = SettingsDialog(self)
        dlg.exec()

    # ═══════════════════════════════════════════════════════════════
    #  ВСПОМОГАТЕЛЬНЫЕ
    # ═══════════════════════════════════════════════════════════════

    def _set_header(self, title: str, hint: str = ""):
        """Обновляет заголовок и подсказку над контентом."""
        self.lbl_title.setText(title)
        self.lbl_hint.setText(hint or "")

    @staticmethod
    def _get_logo_base64() -> Optional[str]:
        """Получает base64 логотипа."""
        try:
            from app.resources.logo import LOGO_BASE64
            return LOGO_BASE64
        except (ImportError, AttributeError):
            return None

    def closeEvent(self, event):
        """Корректное завершение: закрытие пула БД."""
        logger.info("Закрытие приложения...")
        from app.core.database import db_manager
        db_manager.close()
        event.accept()
