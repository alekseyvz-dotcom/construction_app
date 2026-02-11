"""
Настройка логирования приложения.
"""
import sys
import logging
from pathlib import Path


def get_app_dir() -> Path:
    """Определяет директорию запущенного .exe или .py файла."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def setup_logging(level: int = logging.DEBUG) -> Path:
    """
    Инициализирует логирование в файл и консоль.
    Возвращает путь к файлу лога.
    """
    log_file = get_app_dir() / "main_app_log.txt"

    # Корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Формат
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Файловый обработчик
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    root_logger.addHandler(file_handler)

    # Консольный обработчик (для отладки)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    root_logger.addHandler(console_handler)

    logging.debug("=== Логирование инициализировано ===")
    return log_file
