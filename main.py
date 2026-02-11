"""
Точка входа приложения.
Инициализация, splash screen, запуск главного окна.
"""
import sys
import logging


def main():
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import QTimer

    app = QApplication(sys.argv)
    app.setApplicationName("Управление строительством")
    app.setOrganizationName("ConstructionSuite")

    # 1. Splash screen
    from app.splash_screen import SplashScreen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Переменная для хранения ссылки на окно
    main_window = None

    def start_application():
        nonlocal main_window

        try:
            # Логирование
            splash.update_status("Инициализация логирования...")
            from app.core.logging_config import setup_logging
            log_file = setup_logging()

            _logger = logging.getLogger(__name__)
            _logger.info("=== Запуск приложения ===")
            _logger.info("Лог-файл: %s", log_file)

            # Настройки
            splash.update_status("Загрузка настроек...")
            from app.core.settings_manager import settings
            settings.load()

            # Проверка провайдера
            provider = settings.db_provider.strip().lower()
            if provider != "postgres":
                raise RuntimeError(
                    f"Ожидался provider=postgres, "
                    f"в настройках: {provider!r}"
                )

            db_url = settings.database_url.strip()
            if not db_url:
                raise RuntimeError(
                    "В настройках не указана строка подключения "
                    "(DATABASE_URL)"
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

            # Закрываем splash
            splash.close()

            # Запуск главного окна
            _logger.info("Запуск главного окна.")
            from app.main_window import MainWindow
            main_window = MainWindow()
            main_window.show()

        except Exception as e:
            splash.close()
            logging.critical(
                "Ошибка инициализации", exc_info=True,
            )
            QMessageBox.critical(
                None,
                "Критическая ошибка",
                f"Не удалось запустить приложение.\n\n"
                f"Ошибка: {e}\n\n"
                f"Проверьте настройки и доступность БД.",
            )
            app.quit()
            return

    # Запуск с задержкой
    QTimer.singleShot(100, start_application)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
