"""
Менеджер настроек приложения.

Хранит настройки в зашифрованном файле settings.dat.
Отвечает ТОЛЬКО за чтение/запись настроек. Никакого GUI.
"""
import os
import sys
import json
import logging
import configparser
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.crypto import encrypt_dict, decrypt_dict
from app.core.database import db_manager

logger = logging.getLogger(__name__)


# ─── Определение директорий ─────────────────────────────────────────

def get_app_dir() -> Path:
    """Директория приложения (рядом с .exe или .py)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


_SETTINGS_FILENAME = "settings.dat"
_CONFIG_INI = "tabel_config.ini"

SETTINGS_PATH = get_app_dir() / _SETTINGS_FILENAME
INI_PATH = get_app_dir() / _CONFIG_INI


# ─── Ключи настроек ─────────────────────────────────────────────────

class Keys:
    """Все ключи настроек в одном месте."""
    # Paths
    SPR = "spravochnik_path"
    OUTPUT_DIR = "output_dir"
    MEALS_ORDERS_DIR = "meals_orders_dir"

    # UI
    SELECTED_DEP = "selected_department"

    # Integrations
    EXPORT_PWD = "export_password"
    PLANNING_PASSWORD = "planning_password"
    ORDERS_MODE = "orders_mode"
    ORDERS_WEBHOOK_URL = "orders_webhook_url"
    PLANNING_ENABLED = "planning_enabled"
    DRIVER_DEPARTMENTS = "driver_departments"
    MEALS_MODE = "meals_mode"
    MEALS_WEBHOOK_URL = "meals_webhook_url"
    MEALS_WEBHOOK_TOKEN = "meals_webhook_token"
    MEALS_PLANNING_ENABLED = "meals_planning_enabled"
    MEALS_PLANNING_PASSWORD = "meals_planning_password"


# ─── Значения по умолчанию ──────────────────────────────────────────

_app_dir = get_app_dir()

DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Paths": {
        Keys.SPR: str(_app_dir / "Справочник.xlsx"),
        Keys.OUTPUT_DIR: str(_app_dir / "Объектные_табели"),
        Keys.MEALS_ORDERS_DIR: str(_app_dir / "Заявки_питание"),
    },
    "DB": {
        "provider": "postgres",
        "database_url": (
            "postgresql://myappuser:QweRty123!change"
            "@185.55.58.31:5432/myappdb?sslmode=disable"
        ),
        "sqlite_path": str(_app_dir / "app_data.sqlite3"),
        "sslmode": "require",
    },
    "UI": {
        Keys.SELECTED_DEP: "Все",
    },
    "Integrations": {
        Keys.EXPORT_PWD: "2025",
        Keys.PLANNING_PASSWORD: "2025",
        Keys.ORDERS_MODE: "webhook",
        Keys.ORDERS_WEBHOOK_URL: "",
        Keys.PLANNING_ENABLED: "false",
        Keys.DRIVER_DEPARTMENTS: "",
        Keys.MEALS_MODE: "webhook",
        Keys.MEALS_WEBHOOK_URL: "",
        Keys.MEALS_WEBHOOK_TOKEN: "",
        Keys.MEALS_PLANNING_ENABLED: "true",
        Keys.MEALS_PLANNING_PASSWORD: "2025",
    },
}


# ─── Хранилище ──────────────────────────────────────────────────────

class SettingsManager:
    """
    Синглтон для управления настройками.

    Использование:
        settings = SettingsManager()
        settings.load()
        url = settings.get("DB", "database_url")
        settings.set("UI", "selected_department", "Монтаж")
        settings.save()
    """

    _instance: Optional["SettingsManager"] = None
    _store: Dict[str, Dict[str, Any]]
    _loaded: bool

    def __new__(cls) -> "SettingsManager":
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._store = {}
            inst._loaded = False
            cls._instance = inst
        return cls._instance

    # ── Чтение / запись файла ────────────────────────────────────

    def load(self) -> None:
        """Загружает настройки из зашифрованного файла."""
        if SETTINGS_PATH.exists():
            try:
                raw = SETTINGS_PATH.read_bytes()
                loaded = decrypt_dict(raw)
                if isinstance(loaded, dict):
                    self._store = loaded
                else:
                    self._store = {}
            except Exception:
                logger.exception("Ошибка чтения settings.dat")
                self._store = {}
        else:
            self._store = {}

        self._ensure_defaults()
        self._loaded = True

        # Создать файл, если его не было
        if not SETTINGS_PATH.exists():
            self.save()

        logger.info("Настройки загружены из %s", SETTINGS_PATH)

    def save(self) -> None:
        """Сохраняет настройки в зашифрованный файл."""
        self._ensure_defaults()
        blob = encrypt_dict(self._store)
        SETTINGS_PATH.write_bytes(blob)
        logger.debug("Настройки сохранены в %s", SETTINGS_PATH)

    def ensure_loaded(self) -> None:
        """Загружает настройки, если ещё не загружены."""
        if not self._loaded:
            self.load()

    # ── Миграция из INI ──────────────────────────────────────────

    def migrate_from_ini(self) -> None:
        """Мигрирует настройки из старого tabel_config.ini."""
        cfg = configparser.ConfigParser()
        if INI_PATH.exists():
            try:
                cfg.read(INI_PATH, encoding="utf-8")
                logger.info("Миграция настроек из %s", INI_PATH)
            except Exception:
                logger.exception("Ошибка чтения INI")

        # Начинаем с дефолтов
        self._store = json.loads(json.dumps(DEFAULTS))

        # Перезаписываем из INI, если есть
        for section in self._store:
            if cfg.has_section(section):
                for key in self._store[section]:
                    val = cfg.get(section, key, fallback=None)
                    if val is not None:
                        self._store[section][key] = val

        self.save()

    # ── Доступ к значениям ───────────────────────────────────────

    def get(
        self,
        section: str,
        key: str,
        fallback: Optional[str] = None,
    ) -> str:
        """Получить значение настройки."""
        self.ensure_loaded()
        val = self._store.get(section, {}).get(key)
        if val is None or val == "":
            if fallback is not None:
                return fallback
            return DEFAULTS.get(section, {}).get(key, "")
        return str(val)

    def get_bool(self, section: str, key: str) -> bool:
        """Получить булево значение."""
        val = self.get(section, key).strip().lower()
        return val in ("1", "true", "yes", "on")

    def set(self, section: str, key: str, value: Any) -> None:
        """Установить значение (без автосохранения)."""
        self.ensure_loaded()
        self._store.setdefault(section, {})[key] = value

    def get_section(self, section: str) -> Dict[str, Any]:
        """Получить всю секцию как dict."""
        self.ensure_loaded()
        return dict(self._store.get(section, {}))

    def set_section(self, section: str, data: Dict[str, Any]) -> None:
        """Перезаписать всю секцию."""
        self.ensure_loaded()
        self._store[section] = dict(data)

    @property
    def store(self) -> Dict[str, Dict[str, Any]]:
        """Прямой доступ к хранилищу (для диалога настроек)."""
        self.ensure_loaded()
        return self._store

    # ── Удобные свойства ─────────────────────────────────────────

    @property
    def db_provider(self) -> str:
        return self.get("DB", "provider")

    @property
    def database_url(self) -> str:
        return self.get("DB", "database_url")

    @property
    def db_sslmode(self) -> str:
        return self.get("DB", "sslmode")

    @property
    def sqlite_path(self) -> str:
        return self.get("DB", "sqlite_path")

    @property
    def spr_path(self) -> Path:
        raw = self.get("Paths", Keys.SPR)
        return Path(os.path.expandvars(raw))

    @property
    def output_dir(self) -> Path:
        raw = self.get("Paths", Keys.OUTPUT_DIR)
        return Path(os.path.expandvars(raw))

    @property
    def meals_orders_dir(self) -> Path:
        raw = self.get("Paths", Keys.MEALS_ORDERS_DIR)
        return Path(os.path.expandvars(raw))

    @property
    def export_password(self) -> str:
        return self.get("Integrations", Keys.EXPORT_PWD)

    @property
    def selected_department(self) -> str:
        return self.get("UI", Keys.SELECTED_DEP)

    @selected_department.setter
    def selected_department(self, value: str) -> None:
        self.set("UI", Keys.SELECTED_DEP, value or "Все")
        self.save()

    @property
    def meals_mode(self) -> str:
        return self.get("Integrations", Keys.MEALS_MODE).strip().lower()

    @meals_mode.setter
    def meals_mode(self, value: str) -> None:
        self.set("Integrations", Keys.MEALS_MODE, value or "webhook")
        self.save()

    @property
    def meals_webhook_url(self) -> str:
        return self.get("Integrations", Keys.MEALS_WEBHOOK_URL)

    @meals_webhook_url.setter
    def meals_webhook_url(self, value: str) -> None:
        self.set("Integrations", Keys.MEALS_WEBHOOK_URL, value or "")
        self.save()

    @property
    def meals_webhook_token(self) -> str:
        return self.get("Integrations", Keys.MEALS_WEBHOOK_TOKEN)

    @meals_webhook_token.setter
    def meals_webhook_token(self, value: str) -> None:
        self.set("Integrations", Keys.MEALS_WEBHOOK_TOKEN, value or "")
        self.save()

    @property
    def meals_planning_enabled(self) -> bool:
        return self.get_bool("Integrations", Keys.MEALS_PLANNING_ENABLED)

    @meals_planning_enabled.setter
    def meals_planning_enabled(self, value: bool) -> None:
        self.set(
            "Integrations", Keys.MEALS_PLANNING_ENABLED,
            "true" if value else "false",
        )
        self.save()

    @property
    def meals_planning_password(self) -> str:
        return self.get("Integrations", Keys.MEALS_PLANNING_PASSWORD)

    @meals_planning_password.setter
    def meals_planning_password(self, value: str) -> None:
        self.set("Integrations", Keys.MEALS_PLANNING_PASSWORD, value or "")
        self.save()

    # ── Внутреннее ───────────────────────────────────────────────

    def _ensure_defaults(self) -> None:
        """Заполняет отсутствующие секции/ключи значениями по умолчанию."""
        for section, defaults in DEFAULTS.items():
            self._store.setdefault(section, {})
            for key, default_val in defaults.items():
                if key not in self._store[section]:
                    self._store[section][key] = default_val


# ─── Глобальный экземпляр ───────────────────────────────────────────

settings = SettingsManager()


# ─── Обратная совместимость (функции-обёртки) ────────────────────────
# Эти функции нужны, чтобы старые модули продолжали работать
# пока мы не перепишем их все.

def ensure_config():
    settings.ensure_loaded()

def get_db_provider() -> str:
    return settings.db_provider

def get_database_url() -> str:
    return settings.database_url

def get_db_sslmode() -> str:
    return settings.db_sslmode

def get_spr_path_from_config() -> Path:
    return settings.spr_path

def get_output_dir_from_config() -> Path:
    return settings.output_dir

def get_meals_orders_dir_from_config() -> Path:
    return settings.meals_orders_dir

def get_export_password_from_config() -> str:
    return settings.export_password

def get_selected_department_from_config() -> str:
    return settings.selected_department

def set_selected_department_in_config(dep: str):
    settings.selected_department = dep

def get_meals_mode_from_config() -> str:
    return settings.meals_mode

def set_meals_mode_in_config(mode: str):
    settings.meals_mode = mode

def get_meals_webhook_url_from_config() -> str:
    return settings.meals_webhook_url

def set_meals_webhook_url_in_config(url: str):
    settings.meals_webhook_url = url

def get_meals_webhook_token_from_config() -> str:
    return settings.meals_webhook_token

def set_meals_webhook_token_in_config(tok: str):
    settings.meals_webhook_token = tok

def get_meals_planning_enabled_from_config() -> bool:
    return settings.meals_planning_enabled

def set_meals_planning_enabled_in_config(enabled: bool):
    settings.meals_planning_enabled = enabled

def get_meals_planning_password_from_config() -> str:
    return settings.meals_planning_password

def set_meals_planning_password_in_config(pwd: str):
    settings.meals_planning_password = pwd
