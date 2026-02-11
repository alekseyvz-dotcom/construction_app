"""
Домашняя страница с логотипом и приветствием.
"""
import base64
import logging
from io import BytesIO

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

logger = logging.getLogger(__name__)


class HomePage(QWidget):
    """Домашняя страница приложения."""

    def __init__(self, logo_base64: str = None, parent=None):
        super().__init__(parent)
        self._logo_b64 = logo_base64
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        # Логотип
        if self._logo_b64:
            pixmap = self._load_logo(self._logo_b64, max_w=360, max_h=360)
            if pixmap and not pixmap.isNull():
                logo_label = QLabel()
                logo_label.setPixmap(pixmap)
                logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(logo_label)

        # Приветствие
        welcome = QLabel("Добро пожаловать!")
        welcome.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome)

        hint = QLabel("Выберите раздел в меню навигации.")
        hint.setFont(QFont("Segoe UI", 10))
        hint.setStyleSheet("color: #444;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    @staticmethod
    def _load_logo(b64_data: str, max_w: int = 360, max_h: int = 360) -> QPixmap:
        """Загружает логотип из base64 строки."""
        try:
            raw = base64.b64decode(b64_data.strip())
            pixmap = QPixmap()
            pixmap.loadFromData(raw)
            if pixmap.isNull():
                return QPixmap()
            return pixmap.scaled(
                max_w, max_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        except Exception as e:
            logger.error("Ошибка загрузки логотипа: %s", e)
            
