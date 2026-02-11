"""
Страница входа в систему.
"""
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QSpacerItem,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.core.auth import authenticate_user

logger = logging.getLogger(__name__)


class LoginPage(QWidget):
    """Виджет страницы входа."""

    # Сигнал испускается при успешном логине, передаёт dict пользователя
    login_successful = Signal(dict)
    # Сигнал для запроса выхода из приложения
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        # Основной layout — центрирование
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Контейнер формы
        container = QWidget()
        container.setObjectName("LoginContainer")
        container.setFixedWidth(380)
        container.setStyleSheet(
            """
            #LoginContainer {
                background-color: white;
                border-radius: 8px;
                padding: 32px;
            }
            """
        )

        form_layout = QVBoxLayout(container)
        form_layout.setSpacing(8)

        # Заголовок
        lbl_title = QLabel("Управление строительством")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(lbl_title)

        lbl_subtitle = QLabel("Вход в систему")
        lbl_subtitle.setFont(QFont("Segoe UI", 11))
        lbl_subtitle.setStyleSheet("color: #555;")
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addWidget(lbl_subtitle)

        form_layout.addSpacing(16)

        # Поля ввода
        grid = QGridLayout()
        grid.setSpacing(8)

        grid.addWidget(QLabel("Логин:"), 0, 0, Qt.AlignmentFlag.AlignRight)
        self.input_login = QLineEdit()
        self.input_login.setPlaceholderText("Введите логин")
        self.input_login.setMinimumWidth(220)
        grid.addWidget(self.input_login, 0, 1)

        grid.addWidget(QLabel("Пароль:"), 1, 0, Qt.AlignmentFlag.AlignRight)
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Введите пароль")
        self.input_password.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(self.input_password, 1, 1)

        form_layout.addLayout(grid)
        form_layout.addSpacing(16)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_login = QPushButton("Войти")
        self.btn_login.setMinimumWidth(100)
        self.btn_login.clicked.connect(self._on_login)
        btn_layout.addWidget(self.btn_login)

        self.btn_exit = QPushButton("Выход")
        self.btn_exit.setObjectName("SecondaryButton")
        self.btn_exit.setMinimumWidth(80)
        self.btn_exit.clicked.connect(self.exit_requested.emit)
        btn_layout.addWidget(self.btn_exit)

        form_layout.addLayout(btn_layout)

        outer.addWidget(container)

        # Enter для входа
        self.input_login.returnPressed.connect(self._on_login)
        self.input_password.returnPressed.connect(self._on_login)

    def _on_login(self):
        username = self.input_login.text().strip()
        password = self.input_password.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Вход", "Укажите логин и пароль.")
            return

        try:
            user = authenticate_user(username, password)
        except Exception as e:
            logger.exception("Ошибка БД при аутентификации")
            QMessageBox.critical(
                self, "Ошибка", f"Ошибка при обращении к БД:\n{e}"
            )
            return

        if not user:
            QMessageBox.warning(self, "Вход", "Неверный логин или пароль.")
            self.input_password.clear()
            self.input_password.setFocus()
            return

        logger.info("Пользователь '%s' успешно вошёл", username)
        self.login_successful.emit(user)

    def reset(self):
        """Очищает поля для повторного входа."""
        self.input_login.clear()
        self.input_password.clear()
        self.input_login.setFocus()
