"""
Заставка (Splash Screen) при загрузке приложения.
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class SplashScreen(QWidget):
    """Окно-заставка при запуске приложения."""

    def __init__(self):
        super().__init__()
        self.setObjectName("SplashWindow")
        self.setWindowTitle("Загрузка...")
        self.setFixedSize(450, 250)

        # Убираем рамки окна
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        # Центрируем на экране
        self._center_on_screen()

        # Компоновка
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 20)

        # Заголовок
        title = QLabel("Управление строительством")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Подзаголовок
        subtitle = QLabel("Пожалуйста, подождите...")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Прогресс-бар
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(0)  # Indeterminate mode
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        layout.addStretch()

        # Статус
        self.status_label = QLabel("Инициализация...")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setStyleSheet("color: #555;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.setStyleSheet(
            """
            #SplashWindow {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
            }
            """
        )

    def update_status(self, text: str) -> None:
        """Обновляет текст статуса."""
        self.status_label.setText(text)
        # Принудительно обрабатываем события GUI
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def _center_on_screen(self) -> None:
        """Центрирует окно на экране."""
        from PySide6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)
