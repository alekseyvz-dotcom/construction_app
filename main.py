"""
Точка входа приложения.
Инициализация, splash screen, запуск главного окна.
"""
import sys
import logging

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Управление строительством")
    app.setOrganizationName("ConstructionSuite")

    # ── 1. Splash screen ─────────────────────────────────────────
    from app.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # ── 2. Отложенная инициализация ──────────────────────────────
    def start_application():
        try:
            # Логирование
            splash.update_status("Инициализация логирования...")
            from app.core.logging_config import setup_logging
            setup_logging()
            logger = logging.getLogger(__name__)
            logger.info("=== Запуск приложения ===")

            # Настройки
            splash.update_status("Загрузка настроек...")
            from app.core.settings_manager import settings
            settings.load()

            # Проверка провайдера
            provider = settings.db_provider.strip().lower()
            if provider != "postgres":
                raise RuntimeError(
                    f"Ожидался provider=postgres, в настройках: {provider!r}"
                )

            db_url = settings.database_url.strip()
            if not db_url:
                raise RuntimeError(
                    "В настройках не указана строка подключения (DATABASE_URL)"
                )

            # Подключение к БД
            splash.update_status("Подключение к базе данных...")
            from app.core.database import db_manager
            db_manager.initialize(
                database_url=db_url,
                sslmode=settings.db_sslmode,
            )

            # Синхронизация прав
            splash.update_status("Синхронизация прав доступа...")
            from app.core.permissions import sync_permissions_from_menu_spec
            sync_permissions_from_menu_spec()

            # Передача пула в старые модули (обратная совместимость)
            splash.update_status("Инициализация модулей...")
            _init_legacy_modules(db_manager)

            # Закрываем splash
            splash.close()

            # Запускаем главное окно
            logger.info("Инициализация завершена. Запуск главного окна.")
            from app.main_window import MainWindow
            window = MainWindow()

            # Регистрация страниц из модулей
            _register_all_pages(window)

            window.show()

        except Exception as e:
            splash.close()
            logging.critical(
                "Ошибка инициализации", exc_info=True,
            )
            QMessageBox.critical(
                None, "Критическая ошибка",
                f"Не удалось запустить приложение.\n\n"
                f"Ошибка: {e}\n\n"
                f"Проверьте настройки и доступность БД.",
            )
            sys.exit(1)

    # ── 3. Запуск с задержкой (чтобы splash успел отрисоваться) ──
    QTimer.singleShot(100, start_application)

    sys.exit(app.exec())


def _init_legacy_modules(db_mgr):
    """
    Передаёт пул соединений в старые модули,
    которые ещё не переписаны на новую архитектуру.
    """
    # Список модулей, у которых есть set_db_pool()
    module_names = [
        "meals_module",
        "meals_reports",
        "SpecialOrders",
        "objects",
        "timesheet_module",
        "analytics_module",
        "employees",
        "timesheet_compare",
        "meals_employees",
        "lodging_module",
        "employee_card",
    ]

    pool = db_mgr._pool  # SimpleConnectionPool для обратной совместимости

    for name in module_names:
        try:
            mod = __import__(name)
            if hasattr(mod, "set_db_pool"):
                mod.set_db_pool(pool)
                logging.debug("set_db_pool() -> %s", name)
        except ImportError:
            logging.debug("Модуль %s не найден (пропускаем)", name)
        except Exception:
            logging.exception("Ошибка инициализации модуля %s", name)


def _register_all_pages(window):
    """
    Регистрирует построители страниц из всех модулей.
    Каждый модуль, который мы ещё не переписали, оборачивается
    в адаптер, создающий QWidget-обёртку.
    """
    # Пример регистрации (раскомментируйте по мере переноса модулей):
    #
    # from app.modules.timesheet import create_timesheet_page
    # window.register_page("timesheet", create_timesheet_page)
    #
    # Для старых tkinter-модулей пока не регистрируем —
    # они будут добавляться по мере переписывания.

    logging.info(
        "Зарегистрировано страниц: %d",
        len(window._page_builders),
    )


if __name__ == "__main__":
    main()
